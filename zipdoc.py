# zipdoc.py - Mercurial filter for uncompressed storage of zipped documents
#
# Copyright 2011 Andreas Gobell
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.
#
# Enhanced for "pretty XML" 2014 by Thorsten Weimann
#
# Changes to make this extension work with Python 3 2023 by Laura Bromley

'''Encode/decode filter for uncompressed storage of zipped document formats

    Overview::

    Some document formats like docx or odt are really ZIP archives containing 
    primarily XML documents. If these documents are version controlled with
    Mercurial the delta compression is not very efficient as these are binary
    formats and every change to the document can significantly change the 
    bytes of the ZIP archive, e.g. the docx or odt file. When the files are
    stored as an uncompressed ZIP they contain the plain XML files plus some
    header information. This way the change only concerns the respective parts
    of the XML files. Thus deltas can be computed more efficiently and the 
    delta compression improves (Note: docx and odt files also contain small 
    binary thumbnail images that change as well). 

Installation::
  
    The extension is enabled by specifying its path in the ``extension``
    section of an ``hgrc`` file. If the extension is located in Mercurial's
    ``hgext`` folder the path can be omitted.
        
    [extensions]  
    hgext.zipdoc = /path/to/zipdoc.py

Configuration::

    For every file format that is a zipped archive and should be stored
    uncompressed an encode/decode pair has to be added:

    [encode]
    **.docx = zipdocencode
    **.docm = zipdocencode
    **.dotx = zipdocencode
    **.dotm = zipdocencode
    **.odt = zipdocencode

    [decode]
    **.docx = zipdocdecode
    **.docm = zipdocdecode
    **.dotx = zipdocdecode
    **.dotm = zipdocdecode
    **.odt = zipdocdecode
    
How it works::

    On every write to the repository (e.g. commit) the encode filter
    recompresses the zipped document file without any compression. This 
    uncompressed version will be managed by Mercurial. At first the space
    consumption of the repository might be higher compared to version 
    controlling an compressed document but after some changes to the document 
    the better delta compression of the uncompressed file will result in 
    clearly less space consumption.

    On every read from the repository (e.g. update, archive) the decode filter
    will recompress the zipped document file with compression. This way the 
    file will consume less space in the working directory.
    
Notes and Tips::

    Differing file sizes    
    
    A file read from a Mercurial repository might be smaller than the same 
    file saved by the respective application. This is due to different
    compression levels used by this filter and the application. E.g. if 
    you have a docx file saved by Microsoft Word, commit it to the repository
    and archive the committed file with Mercurial (or do an update where the 
    file will be replaced) the archived file will probably be smaller than the 
    one written by Word. This is no problem just keep this in mind if you are
    comparing file sizes or wonder why a file suddenly got larger after saving
    with the application.
    
    Viewing the document's XML text in diff
    
    When using the diff command specifying the ``-a`` (or ``--text``) option
    tells Mercurial to treat the file as text. This way you are able to see
    the changes to the XML that are contained in the uncompressed zip stored
    in the repository. Note that this does not work if git style diff is used.
    
    Plain zip files
    
    This extensions makes no assumptions about the specific format of the
    filtered zip file. Thus any file that is a valid zip archive can be
    processed with this filter.
    
    Checking if the extension works
    
    By using the ``--debug`` option for a Mercurial command you will get
    debug messages from ZipDoc for every file that is encoded or decoded.
    This can be used to check if the extension is working and which files are
    processed.
    
'''

import zipfile

from mercurial import util, ui, hg
from mercurial.i18n import _

from io import BytesIO 


def zipdocencode(s, cmd, **kwargs):
    '''Encode filter: uncompresses the zipped document format when writing
    to the repository.'''
    # wrap string representation of the file provided by Mercurial
    # in a file-like object that can be used with zipfile
    infile = BytesIO(s)
    # open the file as a zip archive
    # if the file is not a zip archive (e.g. because the file is a link having
    # the same extension) just use the regular file's string representation
    try:
        zipped = zipfile.ZipFile(infile, "r")
    except zipfile.BadZipfile:
        # use note level instead of warn: 
        # a warning might irritate users although there is not really a
        # problem as the file will still be version controlled unfiltered
        # without the improved delta compression. The only problem is a
        # broken zip but thats beyond our scope.
        kwargs["ui"].note(_("zipdoc: Skipped encoding '" + kwargs["filename"]
                + "' due to bad ZIP archive. The file is not a ZIP"
                + " (might be a link) or the archive is broken.\n"))
        return s
    archive_member_infos = zipped.infolist()
    
    # string wrapper for the output file to return to Mercurial
    outfile = BytesIO()
    uncompressed = zipfile.ZipFile(outfile, "w", zipfile.ZIP_STORED)
        
    for archive_member_info in archive_member_infos:  
        archive_member = zipped.read(archive_member_info)        
        # set to no compression
        archive_member_info.compress_type = 0
        # We must take care of none XML files (printersettings.bin)
        if archive_member_info.filename.lower().endswith('.xml'):
            # Split lines for better diffs
            uncompressed.writestr(archive_member_info,
                                  archive_member.replace(b"><", b">\r\n <"))
        else:
            uncompressed.writestr(archive_member_info, archive_member)
    zipped.close()    
    uncompressed.close()
    infile.close()
    
    outs = outfile.getvalue()    
    outfile.close()
    kwargs["ui"].debug(_("zipdoc: Encoded %s\n") % kwargs["filename"])
    return outs

def zipdocdecode(s, cmd, **kwargs):
    '''Decode filter: compresses the zipped document format when reading from
    the repository.'''
    infile = BytesIO(s)
    try:
        uncompressed = zipfile.ZipFile(infile, "r")
    except zipfile.BadZipfile:
        kwargs["ui"].note(_("zipdoc: Skipped decoding '%s"
                + "' due to bad ZIP archive. The file is not a ZIP"
                + " (might be a link) or the archive is broken.\n")
                % kwargs["filename"])
        return s        
    archive_member_infos = uncompressed.infolist()
    
    outfile = BytesIO()
    zipped = zipfile.ZipFile(outfile, "w", zipfile.ZIP_DEFLATED)
    
    for archive_member_info in archive_member_infos:     
        archive_member = uncompressed.read(archive_member_info)
        # set compression level 
        # (a docx file will be smaller than the one created by Microsoft Word)
        archive_member_info.compress_type = zipfile.ZIP_DEFLATED
        if archive_member_info.filename.lower().endswith('.xml'):
            # Revert splitted lines
            zipped.writestr(archive_member_info,
                            archive_member.replace(b">\r\n <", b"><"))
        else:
            zipped.writestr(archive_member_info, archive_member)
    zipped.close()    
    uncompressed.close()
    infile.close()
    
    outs = outfile.getvalue()    
    outfile.close()
    kwargs["ui"].debug(_("zipdoc: Decoded %s\n") % kwargs["filename"])
    return outs


# define the filter names that are used in the [encode] and [decode] sections
_filters = {
    b'zipdocencode': zipdocencode,
    b'zipdocdecode': zipdocdecode
    }

# register the filter names that are used in the 
# [encode] and [decode] sections
def reposetup(ui, repo):
    if not repo.local():
        return
    for name, fn in _filters.items():
        repo.adddatafilter(name, fn)

