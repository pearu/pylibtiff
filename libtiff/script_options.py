

__all__ = ['set_formatter']

import os
from optparse import OptionGroup, NO_DEFAULT
from optparse import TitledHelpFormatter

class MyHelpFormatter(TitledHelpFormatter):

    def format_option(self, option):
        old_help = option.help
        default = option.default
        if isinstance (default, str) and ' ' in default:
            default = repr (default)
        if option.help is None:
            option.help = 'Specify a %s.' % (option.type) 
        if option.type=='choice':
            choices = []
            for choice in option.choices:
                if choice==option.default:
                    if ' ' in choice:
                        choice = repr(choice)
                    choice = '['+choice+']'
                else:
                    if ' ' in choice:
                        choice = repr(choice)
                choices.append (choice)
            option.help = '%s Choices: %s.'% (option.help, ', '.join(choices))
        else:
            if default != NO_DEFAULT:
                if option.action=='store_false':
                    option.help = '%s Default: %s.'% (option.help, not default)
                else:
                    option.help = '%s Default: %s.'% (option.help, default)

        result = TitledHelpFormatter.format_option (self, option)
        option.help = old_help
        return result

help_formatter = MyHelpFormatter()

def set_formatter(parser):
    """Set customized help formatter.
    """
    parser.formatter = help_formatter

def set_convert_options(parser):
    set_formatter(parser)
    if os.name == 'posix':
        import matplotlib
        matplotlib.use('GTkAgg')
        parser.run_methods = ['subcommand']
    parser.set_usage ('%prog [options] -i INPUTPATH [-o OUTPUTPATH]')
    parser.set_description('Convert INPUTPATH to OUTPUTPATH.')
    parser.add_option ('--input-path', '-i',
                       type = 'file', metavar='INPUTPATH',
                       help = 'Specify INPUTPATH.'
                       )
    parser.add_option ('--output-path', '-o',
                       type = 'file', metavar='OUTPUTPATH',
                       help = 'Specify OUTPUTPATH.'
                       )

