from configobj import ConfigObj
class myConfigObj(ConfigObj):
    COMMENT_MARKERS = ['#', ';']
    def __init__(self,inifile=None, options=None, configspec=None, encoding=None,
                   interpolation=True, raise_errors=False, list_values=True,
                   create_empty=False, file_error=False, stringify=True,
                   indent_type=None, default_encoding=None, unrepr=False,
                   write_empty_values=False, _inspec=False):
        ConfigObj.__init__(self,infile=inifile, options=options, configspec=configspec, encoding=encoding,
                   interpolation=interpolation, raise_errors=raise_errors, list_values=list_values,
                   create_empty=create_empty, file_error=file_error, stringify=stringify,
                   indent_type=indent_type, default_encoding=default_encoding, unrepr=unrepr,
                   write_empty_values=write_empty_values, _inspec=_inspec)