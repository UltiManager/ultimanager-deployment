import json
import subprocess

from .base import BaseStep


class TerraformStep(BaseStep):
    """
    Apply a set of Terraform configurations.
    """

    def __init__(self, name, configuration_directory, env=None, outputs=None):
        self.name = name
        self.configuration_directory = configuration_directory
        self.env = env or {}
        self.outputs = outputs or []

    def run(self, destroy=False, **kwargs):
        self._init()
        self._plan(destroy)

        if not self._prompt():
            return False, {}

        self._apply()

        outputs = self._get_outputs() if not destroy else {}

        return True, outputs

    def _init(self):
        subprocess.run(
            ['terraform', 'init'],
            check=True,
            cwd=self.configuration_directory,
            env=self.env,
        )

    def _plan(self, destroy):
        plan_args = ['terraform', 'plan', '-out', 'tfplan']
        if destroy:
            plan_args.append('-destroy')

        subprocess.run(
            plan_args,
            check=True,
            cwd=self.configuration_directory,
            env=self.env,
        )

    def _prompt(self):
        return self.prompt_yes_no("Would you like to apply the above plan?")

    def _apply(self):
        subprocess.run(
            ['terraform', 'apply', 'tfplan'],
            check=True,
            cwd=self.configuration_directory,
            env=self.env,
        )

    def _get_outputs(self):
        results = subprocess.run(
            ['terraform', 'output', '-json'],
            check=True,
            cwd=self.configuration_directory,
            encoding='utf8',
            env=self.env,
            stdout=subprocess.PIPE,
        )
        raw_outputs = json.loads(results.stdout)

        outputs = {}
        for output_path in self.outputs:
            path_parts = output_path.split(".")

            if len(path_parts) == 1:
                outputs[output_path] = raw_outputs[output_path]['value']
            elif len(path_parts) == 2:
                resource, attr = output_path.split(".")
                outputs[f"{resource}_{attr}"] = raw_outputs[resource]['value'][attr]
            else:
                raise ValueError(
                    f"Path not parsable (too many values): {output_path}"
                )

        return outputs
