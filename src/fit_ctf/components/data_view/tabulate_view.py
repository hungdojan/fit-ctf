from tabulate import tabulate

import fit_ctf.components.data_view.data_view as data_view


class TabulateView(data_view.DataViewInterface):
    @staticmethod
    def print_data(headers: list, values: list[list], **kw):  # pragma: no cover
        print(
            tabulate(
                [["null" if v is None else v for v in rows] for rows in values],
                headers,
                tablefmt="pipe",
                stralign="center",
                **kw,
            )
        )
