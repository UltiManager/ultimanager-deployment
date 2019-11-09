from .base import BaseStep


class LinkGithub(BaseStep):
    """
    Step to prompt the user to manually link GitHub to their GCP
    project.
    """
    name = "link-github"

    def run(self, destroy=False, previous_step_results=None):
        # This manual step is a no-op if destroying.
        if destroy:
            return True, None

        previous_step_results = previous_step_results or {}
        project_step_results = previous_step_results.get('project', {})

        if not project_step_results:
            print("\n\nExpected results from previous step 'project'\n")
            return False, None

        project_id = project_step_results['root_project_id']
        url = f"https://console.cloud.google.com/cloud-build/triggers/connect?project={project_id}"

        print(
            f"\n\nPlease link your GitHub repositories to your GCP project."
            f"Do NOT create any triggers for the repositories:\n\n"
            f"    {url}"
            f"\n\nPress enter to continue..."
        )

        input()

        return True, None
