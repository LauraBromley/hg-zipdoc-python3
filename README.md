# mercurial_zipdoc_python3
## Python 3 version of the mercurial zipdoc extension

The mercurial zipdoc extension (zipdoc.py) is used for version control of document formats which are zip archives (such as .xlsx, .docx, .odt). The extension was originally created in 2011 by Andreas Gobell and was hosted on https://bitbucket.org/gobell/hg-zipdoc/ and it has a wiki page at 
https://wiki.mercurial-scm.org/ZipdocExtension

However the extension was never updated to Python 3, and it it does not work with newer versions of Mercurial. The Bitbucket repository no longer exists.

We have been using this extension in our codebase for some time now and we want to continue with it, but we also want to upgrade to the latest Mercurial. So we have updated zipdoc.py for Python 3.

Note that no attempt has been made here to get the extension to work with both Python 2 and 3, this version is for Python 3 only.

The following is the original notes on usage, which has not changed:

### Zipdoc: Encode/decode filter for uncompressed storage of zipped document formats

### Overview:

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

### Installation:
  
The extension is enabled by specifying its path in the `extension`
section of an `hgrc` file. If the extension is located in Mercurial's
`hgext` folder the path can be omitted.
        
    [extensions]  
    hgext.zipdoc = /path/to/zipdoc.py

### Configuration:

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
    
### How it works:

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
    
### Notes and Tips:

#### Differing file sizes    

A file read from a Mercurial repository might be smaller than the same 
file saved by the respective application. This is due to different
compression levels used by this filter and the application. E.g. if 
you have a docx file saved by Microsoft Word, commit it to the repository
and archive the committed file with Mercurial (or do an update where the 
file will be replaced) the archived file will probably be smaller than the 
one written by Word. This is no problem just keep this in mind if you are
comparing file sizes or wonder why a file suddenly got larger after saving
with the application.

#### Viewing the document's XML text in diff

When using the diff command specifying the ``-a`` (or ``--text``) option
tells Mercurial to treat the file as text. This way you are able to see
the changes to the XML that are contained in the uncompressed zip stored
in the repository. Note that this does not work if git style diff is used.

#### Plain zip files

This extensions makes no assumptions about the specific format of the
filtered zip file. Thus any file that is a valid zip archive can be
processed with this filter.

#### Checking if the extension works

By using the `--debug` option for a Mercurial command you will get 
debug messages from ZipDoc for every file that is encoded or decoded.
This can be used to check if the extension is working and which files are
processed.

