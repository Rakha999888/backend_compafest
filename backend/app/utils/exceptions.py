class DatasetNotFoundError(Exception):
    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        super().__init__(f"Dataset with ID '{dataset_id}' not found")
