"""Five-question benchmark: measure success, latency, tool usage, citation precision."""
import json, statistics
from agent import Orchestrator
TESTS=[
 ('What is the monthly uptime target?', ['reliability']),
 ('How can caching improve database performance?', ['scaling']),
 ('How should sensitive data be protected?', ['security']),
 ('How much did cloud infrastructure spending increase from 2024 to 2025?', ['cloud']),
 ('What was the research department budget in 2025?', ['finance'])
]
results=[]
for q,expected in TESTS:
    out=Orchestrator().run(q,approve_calculator=True)
    found=set(out.get('sources',[])); cited={c['citation'] for c in out.get('verification',{}).get('verified',[])}
    success=out['status']=='ok' and bool(cited & set(expected))
    results.append({'question':q,'success':success,'latency_ms':out.get('latency_ms'), 'tool_calls':out.get('tool_calls'), 'citation_precision':out.get('verification',{}).get('citation_precision',0),'sources':list(found)})
print(json.dumps({'results':results,'summary':{'success_rate':sum(x['success'] for x in results)/len(results),'mean_latency_ms':statistics.mean(x['latency_ms'] for x in results),'mean_tool_calls':statistics.mean(x['tool_calls'] for x in results),'mean_citation_precision':statistics.mean(x['citation_precision'] for x in results),'total_api_cost_usd':0}},indent=2))
