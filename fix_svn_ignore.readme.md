Fix_SVN_export
==============

An Script to Fix invalid '\r' error in import into new repos with file exported by svndump.

When we use some version of svn client, we may commit logs or set svn ignore files with line terminal with '\r\n'.

If we dump the old repos and we Want to import it into a new repo, Some Error May occurs Like the Lines Followed:

svnadmin: E125005: Invalid property value found in dumpstream; consider repairing the source or using --bypass-prop-validation while loading.
svnadmin: E125005: Cannot accept non-LF line endings in 'svn:log' property

Or Like This:

svnadmin: E125005: Invalid property value found in dumpstream; consider repairing the source or using --bypass-prop-validation while loading.
svnadmin: E125005: Cannot accept non-LF line endings in 'svn:ignore' property

You can just use this script to deal with the dump file and use the new Generated file to import~.

Each Line we Modified will be printed to stdout, You Can verify it to Make Sure That we did the thing right.

Have Fun.