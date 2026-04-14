import pandas as pd


class FoodCSVRepository:
    def __init__(self, path: str):
        self.path = path

    def get_all(self):
        df = pd.read_csv(self.path)
        return df.to_dict(orient="records")