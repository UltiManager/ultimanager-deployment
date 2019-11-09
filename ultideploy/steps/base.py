class BaseStep:
    """
    Defines the behavior of a deployment step.
    """
    name = None

    @staticmethod
    def prompt_yes_no(question, default=False):
        if default:
            options = "[Y]/n"
        else:
            options = "y/[N]"

        prompt = f"{question} ({options}): "

        while True:
            answer = input(prompt)

            if not answer:
                return default

            if answer.lower().startswith('y'):
                return True
            elif answer.lower().startswith('n'):
                return False

            print("Please answer with 'y' or 'n'.")

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
