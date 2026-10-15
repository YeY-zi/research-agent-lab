"""Real local Qwen inference; no API key and no mocked model responses."""
import json
from pathlib import Path
import re
import time
from .agent import SYSTEM
from .tools import SPECS


def parse_calls(text):
    blocks = re.findall(r'<tool_call>\s*(.*?)\s*</tool_call>',text,re.DOTALL)
    if not blocks and text.strip().startswith('{'): blocks = [text.strip()]
    if len(blocks) != 1: raise ValueError('Return exactly one <tool_call> JSON object')
    value = json.loads(blocks[0])
    if not isinstance(value,dict) or not isinstance(value.get('name'),str) or not isinstance(value.get('arguments'),dict):
        raise ValueError('Expected name string and arguments object')
    return value


def observation(name, result):
    """Bound the model context; retain full unmodified results in audit files."""
    if name in ('paper_search','method_extraction'):
        values = []
        for item in result:
            value = dict(item)
            for key in ('text','method_evidence'):
                if key in value and len(value[key]) > 600:
                    value[key] = value[key][:600]
                    value['evidence_truncated_for_model'] = True
            values.append(value)
        return values
    return result


class LocalQwen:
    def __init__(self,model='Qwen/Qwen3-0.6B',revision=None,cache_dir=None,threads=2):
        import torch
        import transformers
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from huggingface_hub import snapshot_download
        torch.set_num_threads(threads)
        torch.manual_seed(0)
        self.torch = torch
        started = time.perf_counter()
        snapshot = snapshot_download(model,revision=revision,cache_dir=cache_dir,
            allow_patterns=['*.json','*.safetensors','*.jinja','merges.txt','vocab.json'])
        self.tokenizer = AutoTokenizer.from_pretrained(snapshot,local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(snapshot,local_files_only=True,dtype=torch.float32)
        self.model.eval()
        self.metadata = {'backend':'transformers_local','model':model,
            'revision':Path(snapshot).name,'dtype':'float32','device':'cpu','threads':threads,
            'torch':torch.__version__,'transformers':transformers.__version__,
            'load_seconds':time.perf_counter()-started,'decoding':'greedy','enable_thinking':False}

    def generate(self,messages,specs):
        tools = [{'type':'function','function':{'name':s['name'],'description':s['description'],
                  'parameters':s['inputSchema']}} for s in specs]
        encoded = self.tokenizer.apply_chat_template(messages,tools=tools,tokenize=True,
            add_generation_prompt=True,enable_thinking=False,return_tensors='pt',return_dict=True)
        started = time.perf_counter()
        with self.torch.inference_mode():
            output = self.model.generate(**encoded,max_new_tokens=192,do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,temperature=None,top_p=None,top_k=None)
        generated = output[0,encoded['input_ids'].shape[1]:]
        text = self.tokenizer.decode(generated,skip_special_tokens=True)
        return {'raw_output':text,'prompt_tokens':int(encoded['input_ids'].shape[1]),
                'completion_tokens':len(generated),'seconds':time.perf_counter()-started}


def local_agent(session,query,backend,max_steps=12):
    prompt = SYSTEM + '\nCall exactly one tool per turn using <tool_call>{"name":"tool_name","arguments":{...}}</tool_call>. Respect the user-specified config exactly.'
    messages = [{'role':'system','content':prompt},{'role':'user','content':query}]
    specs = getattr(session,'specs',SPECS)
    for step in range(max_steps):
        record = backend.generate(messages,specs)
        record['round'] = step+1
        session.model_trace.append(record)
        try:
            call = parse_calls(record['raw_output'])
        except (ValueError,TypeError) as exc:
            record.update(parsed=False,error=str(exc))
            messages += [{'role':'assistant','content':record['raw_output']},
                         {'role':'user','content':f'Invalid tool response: {exc}. Return one valid tool call.'}]
            print(f'LLM round {step+1}: invalid output ({record["seconds"]:.2f}s)',flush=True)
            continue
        record.update(parsed=True,tool=call['name'],arguments=call['arguments'])
        ident = f'local-{step+1}'
        messages.append({'role':'assistant','content':'','tool_calls':[
            {'id':ident,'type':'function','function':{'name':call['name'],'arguments':json.dumps(call['arguments'])}}]})
        try:
            value = session.call(call['name'],call['arguments'])
            payload = {'ok':True,'result':observation(call['name'],value)}
            record['tool_ok'] = True
        except Exception as exc:
            payload = {'ok':False,'error':f'{type(exc).__name__}: {exc}'}
            record.update(tool_ok=False,tool_error=payload['error'])
        messages.append({'role':'tool','tool_call_id':ident,'content':json.dumps(payload)})
        print(f'LLM round {step+1}: {call["name"]}, ok={record["tool_ok"]}, tokens={record["completion_tokens"]}, {record["seconds"]:.2f}s',flush=True)
        if 'report' in session.state: return
    raise RuntimeError('Local LLM step budget exhausted; no completed report')
