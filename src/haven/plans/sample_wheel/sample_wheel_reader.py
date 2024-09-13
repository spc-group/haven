import re
import pandas as pd

from energy_ranges import (
    E_step_to_k_step,
    ERange,
    KRange,
    energy_to_wavenumber,
    k_step_to_E_step,
    merge_ranges,
    wavenumber_to_energy,
)

def clean_column_names(columns):
    # Convert to lowercase, replace spaces with underscores, and remove non-alphanumeric characters
    return [re.sub(r'[^\w]', '', col.lower().replace(' ', '_')) if isinstance(col, str) else col for col in columns]


def convert_energy_range(energy_range_str):
    """Converts the energy range string into a list of numeric values, applying convert_k_to_E where needed."""
    energy_list = []
    for item in energy_range_str.split():
        if 'k' in item:
            # Remove the 'k' and apply the convert_k_to_E function
            k = float(item.replace('k', ''))
            E = wavenumber_to_energy(k)
            energy_list.append(E)
        else:
            # Convert to float for other values
            energy_list.append(float(item))
    return energy_list

# write pytest to test these functions