
# Only works if IPython is installed.
# To use, place the following line wherever in the program you want to drop to
# an interpreter (can be always forced or can be more strategic like after a
# conditional statement, etc.)

"""
from epucontrol import ipshell; ipshell("")
"""

# Do not *ever* commit a line like that to the repository!  epucontrol
# should be able to be scriptable etc., not always require a human.

ipshell = None
try:
    from IPython.Shell import IPShellEmbed
    ipshell = IPShellEmbed('', "Dropping into IPython", "Leaving interpreter")
except:
    pass
