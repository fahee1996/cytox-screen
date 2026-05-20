import pandas as pd
import subprocess
import os
from rdkit import Chem

# Load
df = pd.read_csv('anticancer_unique.csv')
print(f'Loaded: {len(df)} rows')

# Validate SMILES
def is_valid(s):
    try: return Chem.MolFromSmiles(str(s)) is not None
    except: return False

df['valid_smiles'] = df['smiles'].apply(is_valid)
valid_count = df['valid_smiles'].sum()
print(f'Valid SMILES: {valid_count} / {len(df)}')

# Extract valid for prediction
df[df['valid_smiles']][['smiles']].to_csv('_temp_valid.csv', index=False)

# Run 3 predictions
CKPT = 'final_checkpoints'
FLAGS = '--features_generator rdkit_2d_normalized --no_features_scaling'

models = {
    'cytotox_hepg2':  f'{CKPT}/cytotox_hepg2',
    'cytotox_hskmc':  f'{CKPT}/cytotox_primary',
    'cytotox_imr90':  f'{CKPT}/cytotox_imr90',
}

for name, ckpt_dir in models.items():
    print(f'\nPredicting {name}...')
    cmd = f'chemprop_predict --test_path _temp_valid.csv --checkpoint_dir {ckpt_dir} --preds_path _pred_{name}.csv {FLAGS}'
    subprocess.run(cmd, shell=True, check=True)

    pred = pd.read_csv(f'_pred_{name}.csv')
    df[name] = None
    df.loc[df['valid_smiles'], name] = pred.iloc[:, 1].values
    col_mean = pd.to_numeric(df.loc[df['valid_smiles'], name]).mean()
    print(f'  {name} done: mean={col_mean:.3f}')

# Save
df.to_csv('anticancer_unique.csv', index=False)
print(f'\nSaved: anticancer_unique.csv')
print('New columns added: valid_smiles, cytotox_hepg2, cytotox_hskmc, cytotox_imr90')
print('\nScore interpretation:')
print('  < 0.2 = predicted NON-CYTOTOXIC to that cell line')
print('  > 0.5 = predicted CYTOTOXIC to that cell line')

# Cleanup
for f in ['_temp_valid.csv', '_pred_cytotox_hepg2.csv', '_pred_cytotox_hskmc.csv', '_pred_cytotox_imr90.csv']:
    if os.path.exists(f): os.remove(f)
