#!/bin/sh
/usr/local/bin/python setup.py develop
/usr/local/bin/nulsexplorer -c ./config.yaml -p 8080 --host 0.0.0.0
