import json
from collections import Counter

with open('reports/benchmark_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

passes = [r for r in data if r['status'] == 'pass']
fails  = [r for r in data if r['status'] == 'fail']
print(f'Total cases : {len(data)}')
print(f'Pass        : {len(passes)} ({len(passes)/len(data)*100:.1f}%)')
print(f'Fail        : {len(fails)} ({len(fails)/len(data)*100:.1f}%)')

print('\n--- Score distribution ---')
scores = Counter(r['judge']['final_score'] for r in data)
for k, v in sorted(scores.items()):
    print(f'  Score {k}: {v} cases')

print('\n--- Judge Agreement ---')
agree_levels = Counter(r['judge']['agreement_level'] for r in data)
for k, v in sorted(agree_levels.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v} cases')

print('\n--- Conflict detection ---')
conflicts = Counter(r['judge']['conflict_detected'] for r in data)
print(f'  With conflict: {conflicts.get(True, 0)}')
print(f'  No conflict : {conflicts.get(False, 0)}')

print('\n--- Resolution methods ---')
methods = Counter(r['judge']['resolution_method'] for r in data)
for k, v in methods.items():
    print(f'  {k}: {v}')

print('\n--- Fail cases (final_score < 3) ---')
for r in fails:
    print(f"  [{r['judge']['final_score']:.1f}] {r['test_case'][:100]}")
