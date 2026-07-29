from abc import ABC, abstractmethod

class BaseGenerator(ABC):
    """
    Base class for all quiz generators.

    Every quiz generator (MCQ, True/False, Fill in the Blank,
    Short Answer) will inherit from this class.
    """

    @abstractmethod
    def generate(self, text: str):
        """
        Generate quiz questions from the given text.

        Parameters:
            text (str): Input text from which questions are generated.

        Returns:
            list: A list of generated questions.
        """
        pass