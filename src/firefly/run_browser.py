from firefly import run_viewer


class RunBrowserDisplay(run_viewer.RunViewerDisplayBase):
    def __init__(self, root_node=None, args=None, macros=None, **kwargs):
        super().__init__(args=args, macros=macros, **kwargs)
        # Load the list of all runs for the selection widget
        self.db_task(self.load_runs())
