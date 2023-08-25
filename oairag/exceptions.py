class UnsupportedFileFormatException(Exception):
    """
    Raised when unsupported file format is received
    """

    def __init__(self, message, *args):
        self.__message = message
        super().__init__(message, args)

    def __str__(self):
        return self.__message
