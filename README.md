# onearg

A toy language where all functions accept only one argument.

## Dependencies

Python 3, with the `pyparsing` library:

    pip3 install --user pyparsing

## Usage

To run a onearg program:

    python3 interpreter.py examples/test.oa

To print a C-like representation of a onearg program:

    python3 syntax_tree.py examples/test.oa

## Known Issues

Conditionals and looping aren't implemented yet.

Any feature not in the example program is likely broken or missing.

