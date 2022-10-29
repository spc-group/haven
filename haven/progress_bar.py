from bluesky.callbacks import CallbackBase
from tqdm import tqdm


class ProgressBar(CallbackBase):
    num_points: int = 0
    
    """A progress bar that tracks a scan."""
    def start(self, doc):
        self.num_points = doc["num_points"]
        self.plan_name = doc.get("plan_name", "Scanning")
        # Set up the tqdm bar
        self.pbar = tqdm(total=self.num_points, unit="pt", desc=self.plan_name)

    def event(self, doc):
        self.pbar.update(1)

    def stop(self, doc):
        self.pbar.close()
