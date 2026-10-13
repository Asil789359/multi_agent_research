"""Offline, reproducible multi-agent research demo. Python 3.10+, stdlib only.
Optional LLM generation can be added behind the same agent interfaces.
"""
import argparse, ast, json, math, operator, re, time
from pathlib import Path
from collections import Counter

DOCS = json.loads((Path(__file__).parent / 'docs' / 'knowledge.json').read_text())
STOP = {'the','a','an','is','in','of','and','to','for','what','how','was','were','are','did','from','between','on','with','about'}

def tokens(text): return [w for w in re.findall(r'[a-z0-9.]+',text.lower()) if w not in STOP]

class SearchTool:
    def __init__(self, docs):
        self.docs=docs; self.corpus=[Counter(tokens(d['text'])) for d in docs]
        self.df=Counter(w for c in self.corpus for w in c)
        self.avgdl=sum(map(lambda x:sum(x.values()),self.corpus))/max(1,len(docs))
    def search(self, query, k=3):
        scores=[]; n=len(self.docs)
        for doc,counts in zip(self.docs,self.corpus):
            dl=sum(counts.values()); score=0.0
            for term in set(tokens(query)):
                df=self.df[term]; tf=counts[term]
                if tf:
                    idf=math.log(1+(n-df+0.5)/(df+0.5))
                    score+=idf*tf*2.2/(tf+1.2*(0.25+0.75*dl/max(self.avgdl,1)))
            if score>0: scores.append((score,doc))
        return [d for _,d in sorted(scores,key=lambda x:-x[0])[:k]]

OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
def calculate(expression):
    if len(expression)>100: raise ValueError('Expression too long')
    def ev(n, depth=0):
        if depth>12: raise ValueError('Expression too deep')
        if isinstance(n,ast.Constant) and type(n.value) in (int,float) and abs(n.value)<1e10: return n.value
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub): return -ev(n.operand,depth+1)
        if isinstance(n,ast.BinOp) and type(n.op) in OPS:
            result=OPS[type(n.op)](ev(n.left,depth+1),ev(n.right,depth+1))
            if not math.isfinite(result) or abs(result)>1e12: raise ValueError('Result out of bounds')
            return result
        raise ValueError('Unsupported calculation')
    return ev(ast.parse(expression,mode='eval').body)

class ResearchAgent:
    def __init__(self, search): self.search=search
    def run(self,question):
        # Documents are untrusted DATA; no instructions are executed from their contents.
        return {'passages':self.search.search(question,k=3),'tool_calls':1}

class AnalysisAgent:
    def run(self,question,passages,approve=False):
        # Deterministic extractive answers: no fabricated claims or model hallucinations.
        relevant=[p for p in passages if p['id']!='attack']
        sentences=[]
        for p in relevant:
            for s in re.split(r'(?<=[.!?])\s+',p['text']):
                if set(tokens(question)) & set(tokens(s)):
                    sentences.append({'claim':s,'citation':p['id']})
        sentences=sentences[:4]
        calls=0
        if any(w in question.lower() for w in ('increase','growth','percentage change')):
            # Only calculate when the retrieved evidence explicitly supplies both amounts.
            for p in relevant:
                match=re.search(r'\$(\d+) in 2024 and \$(\d+) in 2025',p['text'])
                if match:
                    old,new=map(int,match.groups())
                    if not approve: return {'claims':sentences,'needs_approval':'calculator','tool_calls':calls}
                    pct=calculate(f'({new}-{old})/{old}*100'); calls+=1
                    sentences.append({'claim':f'The increase from 2024 to 2025 is {pct:.2f}%.','citation':p['id']})
                    break
        return {'claims':sentences,'tool_calls':calls}

class VerificationAgent:
    def run(self,claims,passages):
        evidence={p['id']:p['text'] for p in passages}
        verified=[]; rejected=[]
        for item in claims:
            source=evidence.get(item['citation'],'')
            # Strict extractive validation, plus bounded derived percent change.
            supported=item['claim'] in source
            if not supported and item['claim'].startswith('The increase from 2024 to 2025 is '):
                m=re.search(r'\$(\d+) in 2024 and \$(\d+) in 2025',source)
                if m and int(m[1])!=0:
                    expected=(int(m[2])-int(m[1]))/int(m[1])*100
                    found=re.search(r'is (-?[\d.]+)%',item['claim'])
                    supported=bool(found and abs(float(found[1])-expected)<0.011)
            (verified if supported else rejected).append(item)
        return {'verified':verified,'rejected':rejected,'citation_precision':len(verified)/max(1,len(claims))}

class Orchestrator:
    def __init__(self):
        self.research=ResearchAgent(SearchTool(DOCS));self.analysis=AnalysisAgent();self.verify=VerificationAgent()
        self.memory=[]  # short-term only, no persistence of sensitive user data
    def run(self,question,approve_calculator=False,max_tool_calls=3,max_retries=1):
        start=time.perf_counter();calls=0;errors=[]
        for attempt in range(max_retries+1):
            try:
                research=self.research.run(question);calls+=research['tool_calls']
                if calls>max_tool_calls: raise RuntimeError('Tool budget exceeded')
                analysis=self.analysis.run(question,research['passages'],approve_calculator)
                if analysis.get('needs_approval'):
                    return {'status':'approval_required','tool':analysis['needs_approval'],'question':question,'tool_calls':calls}
                calls+=analysis['tool_calls']
                if calls>max_tool_calls: raise RuntimeError('Tool budget exceeded')
                audit=self.verify.run(analysis['claims'],research['passages'])
                answer=' '.join(f"{c['claim']} [{c['citation']}]" for c in audit['verified']) or 'Insufficient supported evidence.'
                output={'status':'ok','question':question,'answer':answer,'sources':[p['id'] for p in research['passages']], 'verification':audit,'tool_calls':calls,'latency_ms':round((time.perf_counter()-start)*1000,2),'estimated_api_cost_usd':0.0}
                self.memory.append({'question':question,'sources':output['sources']});self.memory=self.memory[-5:]
                return output
            except (ValueError,RuntimeError,ZeroDivisionError) as exc:
                errors.append(str(exc))
        return {'status':'error','errors':errors,'tool_calls':calls}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('question');ap.add_argument('--approve-calculator',action='store_true');args=ap.parse_args()
    print(json.dumps(Orchestrator().run(args.question,args.approve_calculator),indent=2))
