class CustomException(Exception):
    """Кастомное исключение."""

    def __init__(self, *args):
        """На случай отсутствия аргументов."""
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        """Сообщение в исключении."""
        print('calling str')
        if self.message:
            return 'MyCustomError, {0} '.format(self.message)
        else:
            return 'MyCustomError has been raised'
