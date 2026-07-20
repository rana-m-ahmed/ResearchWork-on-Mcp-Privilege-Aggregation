import json
with open('phase5/kaggle/official_phase5_runner.ipynb', 'r') as f:
    nb = json.load(f)
for cell in nb['cells']:
    if 'source' in cell and any('run-campaign' in line for line in cell['source']):
        new_source = []
        for line in cell['source']:
            if 'run-campaign' in line and '--max-batches' in line:
                line = line.replace('"--max-batches"', '"--until-safety-horizon","--max-batches"')
            new_source.append(line)
        cell['source'] = new_source
with open('phase5/kaggle/official_phase5_runner.ipynb', 'w') as f:
    json.dump(nb, f, indent=1)
