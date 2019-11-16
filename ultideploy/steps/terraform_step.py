import json
import pathlib
import subprocess
import tempfile

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
        self.print_section("Initialize Terraform")
        self._init()

        with tempfile.TemporaryDirectory() as temp_dir:
            plan_file = pathlib.Path(temp_dir) / 'plan'

            self.print_section("Plan Terraform Changes")
            self._plan(plan_file, destroy)

            if not self._plan_has_changes(plan_file):
                # If the plan has no changes, there's no need to prompt.
                self.print_log("No changes to apply. Continuing.")
            elif not self._prompt():
                return False, None
            else:
                self.print_section("Applying Terraform Changes")
                self._apply(plan_file)

        outputs = self._get_outputs() if not destroy else {}

        return True, outputs

    def _init(self):
        subprocess.run(
            ['terraform', 'init'],
            check=True,
            cwd=self.configuration_directory,
            env=self.env,
        )

    def _plan(self, plan_file, destroy):
        plan_args = ['terraform', 'plan', '-out', plan_file]
        if destroy:
            plan_args.append('-destroy')

        subprocess.run(
            plan_args,
            check=True,
            cwd=self.configuration_directory,
            env=self.env,
        )

    def _plan_has_changes(self, plan_file):
        result = subprocess.check_output(
            ['terraform', 'show', '-json', plan_file],
            cwd=self.configuration_directory,
            encoding='utf8',
            env=self.env,
        )
        plan = json.loads(result)

        for resource in plan['resource_changes']:
            for action in resource['change']['actions']:
                if action != 'no-op':
                    return True

        return False

    def _prompt(self):
        return self.prompt_yes_no("Would you like to apply the above plan?")

    def _apply(self, plan_file):
        subprocess.run(
            ['terraform', 'apply', plan_file],
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
