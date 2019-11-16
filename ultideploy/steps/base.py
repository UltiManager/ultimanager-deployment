import shutil


class BaseStep:
    """
    Defines the behavior of a deployment step.
    """
    name = None

    @staticmethod
    def terminal_width():
        cols, _ = shutil.get_terminal_size((80, 20))

        return cols

    def print_header(self):
        cols = self.terminal_width()

        print("\n\n")
        print("#" * cols)
        print(f"# {self.name.center(cols - 4)} #")
        print("#" * cols)
        print("\n\n")

    def print_log(self, message):
        print(f"[{self.name}] {message}")

    def print_section(self, section_name):
        cols = self.terminal_width()

        print("\n")
        print(f"{self.name}: {section_name}".center(cols))
        print("-" * cols, end="\n\n")

    def prompt_yes_no(self, question, default=False):
        if default:
            options = "[Y]/n"
        else:
            options = "y/[N]"

        prompt = f"[{self.name}] {question} ({options}): "

        while True:
            answer = input(prompt)

            if not answer:
                return default

            if answer.lower().startswith('y'):
                return True
            elif answer.lower().startswith('n'):
                return False

            print("Please answer with 'y' or 'n'.")

    def pre_run(self):
        """
        Called before the step starts running. The default behavior is
        to print out the step's name.
        """
        cols, _ = shutil.get_terminal_size((80, 20))

        self.print_header()

    def run(self, destroy=False, previous_step_results=None):
        """
        Run the deployment step.

        Args:
            destroy:
                A boolean indicating if the resources created by the
                step should be created or destroyed.
            previous_step_results:
                An optional dictionary containing arbitrary data from
                previously run steps.

        Returns:
            A tuple whose first item is a boolean indicating if the
            deployment process should continue and whose second item is
            a dictionary containing the outputs from the step.
        """
        raise NotImplemented("Steps must implement the `run` method.")
