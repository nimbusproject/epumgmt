# This is set up in such a way that you should not need to alter this file to
# add an argument, in most cases.  See em_args.py

import optparse
import em_args
from epumgmt.api.actions import ACTIONS

# Not using yet
EC_VERSION = "X.Y"

# -----------------------------------------------------------------------------

def _add_option(group, arg):
    if arg.boolean:
        _add_boolean_option(group, arg)
    elif arg.string:
        _add_string_option(group, arg)
    else:
        raise Exception("unknown arg type")
        
def _add_string_option(group, arg):
    if arg.short_syntax:
        group.add_option(arg.short_syntax, arg.long_syntax,
                         dest=arg.dest, help=arg.help,
                         metavar=arg.metavar)
    else:
        group.add_option(arg.long_syntax,
                         dest=arg.dest, help=arg.help,
                         metavar=arg.metavar)

def _add_boolean_option(group, arg):
    if arg.short_syntax:
        group.add_option(arg.short_syntax, arg.long_syntax,
                         dest=arg.dest, help=arg.help,
                         action="store_true", default=False)
    else:
        group.add_option(arg.long_syntax,
                         dest=arg.dest, help=arg.help,
                         action="store_true", default=False)

def parsersetup():
    """Return configured command-line parser."""

    ver="Nimbus EPU Management %s - http://www.nimbusproject.org" % EC_VERSION
    usage="epumgmt action [Arguments]"
    parser = optparse.OptionParser(version=ver, usage=usage)

    # ---------------------------------------
    
    # Might be helpful to have more groups in the future.
    actions = ACTIONS().all_actions()
    deprecated_args = []
    other_args = []
    
    for arg in em_args.ALL_EC_ARGS_LIST:
        if arg.deprecated:
            deprecated_args.append(arg)
        else:
            other_args.append(arg)
            
            
    # ---------------------------------------
    actions_title =    "  Actions"
    arguments_title =  "  Arguments"
    deprecated_title = "  Deprecated"
    # For each one, use twice length of the longest one:
    groupline = (len(2*deprecated_title)-1) * "-"


    # Actions
    actions_description = ", ".join(ACTIONS().all_actions())
    group = optparse.OptionGroup(parser, actions_title, actions_description)
    parser.add_option_group(group)

    
    # Arguments
    group = optparse.OptionGroup(parser, arguments_title, groupline)
    for arg in other_args:
        _add_option(group, arg)
    parser.add_option_group(group)

    
    # Deprecated Arguments
    if len(deprecated_args) > 0:
        group = optparse.OptionGroup(parser, grouptxt2, groupline)
        for arg in deprecated_args:
            _add_option(group, arg)
        parser.add_option_group(group)
    
    return parser

def parse(argv):
    """parse arguments from the command line

    The last positional argument will be considered the action.
    """

    if not argv:
        return None, None
    parser = parsersetup()
    opts, args = parser.parse_args(argv)
    try:
        opts.action = args.pop()
    except IndexError:
        # No action specified
        pass

    return opts, args

def print_help():
    """convenience function for printing help from other places in epumgmt
    """
    parser = parsersetup()
    parser.print_help()

def print_version():
    """convenience function for printing version from other places in epumgmt
    """
    parser = parsersetup()
    parser.print_version()
