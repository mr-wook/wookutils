#!/bin/csh
set client="$cwd/beg.py"
set host=localhost
$client $host touch /tmp/touched.tmp
$client $host ls /tmp/touched.tmp
$client $host rm /tmp/touched.tmp
$client $host ls /tmp/touched.tmp

$client $host touch /tmp/foo.bar
$client $host mv /tmp/foo.bar /tmp/foo.barb
$client $host ls /tmp | grep foo
$client $host rm /tmp/foo.barb
$client $host ls /tmp | grep foo
exit 0
