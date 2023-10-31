   #!/bin/csh
   http --json POST localhost:6869/touch/ path=/tmp/touched.tmp
   http --json POST localhost:6869/rm/ path=/home/wook/foo.bar
   http --json POST localhost:6869/touch/ path=/tmp/foo.bar
   http --json POST localhost:6869/rm/ path=/tmp/foo.bar
   http --json POST localhost:6869/touch/ path=/tmp/foo.bar
   http --json POST localhost:6869/move/ source=/tmp/foo.bar dest=/tmp/foo.moved
   http --json POST localhost:6869/rm/ path=/tmp/foo.moved
