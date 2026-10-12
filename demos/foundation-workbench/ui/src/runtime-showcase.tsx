import {useEffect, useState} from 'react';
import './runtime-showcase.css';

type Demo = 'inventory' | 'order_group' | 'equipment' | 'legacy_contract' | 'invalid_contract';
type Mode = 'deterministic' | 'brain';
type Scenario = {snapshot_id:string; title:string};
type ErrorInfo = {error_code:string; message:string; details?:{completion_known?:boolean}};
type Trace = {trace_id:string; plugin_id:string; plugin_version:string; capability:{capability_id:string;version:string}; start:string; end:string; status:string; result:unknown; error:ErrorInfo|null};
type Material = {material_id:string;name:string;unit:string;available:number;demand:number;shortage:number;transfer_quantity:number;transfer_blocked?:boolean};
type Result = {execution_id?:string;task_id?:string;status?:string;output?:{analysis?:{materials:Material[];feasible:boolean};narrative?:string;status?:string;requires_attention?:boolean;entity_id?:string;evidence?:{execution_mode?:string}};trace?:Trace[];error?:ErrorInfo|null;state_effects?:unknown[]};
type Record = {demo:{demo:Demo;snapshot_id:string;mode:Mode;equipment_status:string};request:{execution_id:string;task_id:string;context?:{contract?:{version:string}}};result:Result;business_state_changed:boolean};
type Catalog = {connected:boolean;catalog:{capabilities?:{capability_id:string;version:string}[];error?:ErrorInfo}};

const choices:{id:Demo;title:string;copy:string;symbol:string}[] = [
  {id:'inventory', title:'单订单库存分析', copy:'可用 6 · 需求 10 · 核对缺口', symbol:'▤'},
  {id:'order_group', title:'订单组共同备料', copy:'切换到货、放行与跨层场景', symbol:'◫'},
  {id:'equipment', title:'设备状态检查', copy:'选择状态，检查是否需要关注', symbol:'◇'},
  {id:'legacy_contract', title:'旧数据格式转换', copy:'旧版上下文转换后执行同一能力', symbol:'⇄'},
  {id:'invalid_contract', title:'无效输入拒绝', copy:'提交未注册版本，查看真实错误', symbol:'⊘'},
];
const capabilityNames:{[key:string]:string} = {
  'inventory.analyze':'库存分析', 'equipment.inspect':'设备检查',
  'data_contract.register':'契约注册', 'data_contract.validate':'数据校验',
  'data_contract.transform':'契约转换', 'data_contract.resolve_version':'版本解析',
};
const time = (value:string) => new Date(value).toLocaleTimeString('zh-CN', {hour12:false});
async function request<T>(path:string, body?:unknown):Promise<T> {
  const response = await fetch('/api/v1/runtime'+path, body === undefined ? undefined : {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body),
  });
  const value = await response.json();
  if (!response.ok) throw new Error(typeof value.detail === 'string' ? value.detail : '演示输入未通过校验');
  return value as T;
}

export function RuntimeShowcase({active, scenarios}:{active:boolean;scenarios:Scenario[]}) {
  const [catalog, setCatalog] = useState<Catalog|null>(null);
  const [demo, setDemo] = useState<Demo>('inventory');
  const [snapshot, setSnapshot] = useState('morning');
  const [mode, setMode] = useState<Mode>('deterministic');
  const [equipmentStatus, setEquipmentStatus] = useState('maintenance');
  const [record, setRecord] = useState<Record|null>(null);
  const [history, setHistory] = useState<Record[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [queryNote, setQueryNote] = useState('');
  const [querying, setQuerying] = useState(false);
  useEffect(() => {
    if (!active) return;
    let alive = true;
    request<Catalog>('/capabilities').then(value => {if (alive) setCatalog(value)}).catch(e => {if (alive) setError(e.message)});
    return () => {alive = false};
  }, [active]);

  function changeDemo(value:Demo) {
    setDemo(value); setRecord(null); setError(''); setQueryNote('');
    if (value === 'order_group') setSnapshot('contended');
    if (!['inventory','order_group'].includes(value)) setMode('deterministic');
  }
  function clearResult() {setRecord(null); setError(''); setQueryNote('')}
  async function execute() {
    setBusy(true); clearResult();
    try {
      const value = await request<Record>('/demos', {demo, snapshot_id:snapshot, mode, equipment_status:equipmentStatus});
      setRecord(value); setHistory(rows => [value, ...rows].slice(0,8));
    } catch (e) {setError((e as Error).message)}
    finally {setBusy(false)}
  }
  async function query() {
    if (!record) return;
    setQuerying(true); setQueryNote('');
    try {
      const value = await request<{result?:Result;error?:ErrorInfo}>('/executions/'+record.request.execution_id);
      if (value.error) setQueryNote(value.error.message);
      else if (value.result?.execution_id === record.request.execution_id && value.result.status === record.result.status)
        setQueryNote('已从 Runtime 查询到同一执行编号和状态。');
      else setQueryNote('返回记录与当前执行不一致，请核对原始结果。');
    } catch(e) {setQueryNote((e as Error).message)}
    finally {setQuerying(false)}
  }
  function view(value:Record) {
    setDemo(value.demo.demo); setSnapshot(value.demo.snapshot_id); setMode(value.demo.mode);
    setEquipmentStatus(value.demo.equipment_status); setRecord(value); setError(''); setQueryNote('');
  }
  const result = record?.result;
  const rows = result?.output?.analysis?.materials ?? [];
  const traces = result?.trace ?? [];
  const version = record?.request.context?.contract?.version;
  const unknown = result?.error?.details?.completion_known === false;
  const completed = result?.status === 'COMPLETED';
  const rejected = result?.status === 'FAILED' && record?.demo.demo === 'invalid_contract';
  const title = completed ? '执行完成' : unknown ? '执行结果未确认' : rejected ? '无效输入已被拒绝' : result ? '执行失败' : '等待执行';

  return <div className="runtime-showcase">
    <section className="runtime-hero">
      <div><span className="runtime-new">本轮新增 · MVP 0.1</span><h2>点击执行，查看真实返回。</h2>
        <p>库存、设备与数据契约通过独立 Runtime 执行，每次生成新的执行编号和调用轨迹。</p></div>
      <div className={'runtime-connection '+(catalog?.connected?'online':'offline')}>
        <i/>{catalog ? catalog.connected ? 'Runtime 已连接' : 'Runtime 未连接' : '正在检查连接'}
        <small>只读模拟数据 · 不修改业务库存</small>
      </div>
    </section>
    <div className="runtime-flow"><span>① 选择能力与输入</span><b>→</b><span>② 工作台后台调用 Runtime</span><b>→</b><span>③ 查看实际结果与轨迹</span></div>
    {catalog && !catalog.connected && <div className="alert" role="alert">{catalog.catalog.error?.message ?? '未获得能力目录，请先启动 MVP Runtime。'}</div>}
    {error && <div className="alert" role="alert">{error}</div>}
    <div className="runtime-demo-choices" aria-label="选择 Runtime 验证用例">{choices.map(choice =>
      <button key={choice.id} aria-pressed={demo===choice.id} disabled={busy} className={demo===choice.id?'selected':''} onClick={() => changeDemo(choice.id)}>
        <span>{choice.symbol}</span><b>{choice.title}</b><small>{choice.copy}</small>
      </button>)}</div>
    <section className="runtime-run-panel">
      <div className="runtime-inputs">
        {demo === 'equipment' ? <label>模拟设备状态<select aria-label="模拟设备状态" disabled={busy} value={equipmentStatus} onChange={e => {setEquipmentStatus(e.target.value);clearResult()}}>
          <option value="maintenance">检修中 · 需要关注</option><option value="idle">空闲</option><option value="running">运行中</option><option value="offline">离线 · 需要关注</option>
        </select></label> : <label>使用的模拟截面<select aria-label="Runtime 模拟截面" value={snapshot} disabled={busy} onChange={e => {setSnapshot(e.target.value);clearResult()}}>
          {scenarios.map(value => <option key={value.snapshot_id} value={value.snapshot_id}>{value.title}</option>)}
        </select></label>}
        {['inventory','order_group'].includes(demo) && <label>执行方式<select aria-label="Runtime 执行方式" disabled={busy} value={mode} onChange={e => {setMode(e.target.value as Mode);clearResult()}}>
          <option value="deterministic">直接计算 · 不调用模型</option><option value="brain">官方工厂大脑 · 调用 DeepSeek API</option>
        </select></label>}
        <div className="runtime-run-action"><button className="primary" disabled={busy||!catalog?.connected} onClick={() => void execute()}>{busy?'正在执行…':demo==='invalid_contract'?'执行拒绝验证':'立即执行'} <span>→</span></button>
          <small>{mode==='brain'?'点击后调用官方模型，可能需要几十秒':'点击后真实调用 Runtime 服务，无模型费用'}</small></div>
      </div>
      <p className="runtime-input-note">{demo==='order_group'?'共同核对 ORD-1001 与 ORD-1003，共享库存计一次。':demo==='equipment'?'使用 EQ-001 的模拟状态，不发送设备控制命令。':demo==='legacy_contract'?'输入契约 0.1.0：state 字段转换为 1.0.0 的 factory_state，再执行库存分析。':demo==='invalid_contract'?'提交契约版本 99.0.0，验证 Runtime 如何拒绝未注册版本。':'核对 ORD-001 的伺服电机需求 10 件，初始可用 6 件。'}</p>
    </section>
    <div className="runtime-output-grid"><section className="runtime-result" aria-live="polite">
      <div className="section-head"><h2>本次实际执行结果</h2><span>{busy?'执行中':record?'来自 Runtime 实时返回':'点击上方开始'}</span></div>
      {!record ? <div className="empty"><span>{busy?'◌':'▷'}</span><b>{busy?'正在等待服务返回':'这里显示本次执行的结果'}</b><p>{busy?'不会预填结果。当前执行不改变业务库存。':'选择一个验证用例，然后点击立即执行。'}</p></div> : <>
        <div className={'runtime-verdict '+(completed?'success':unknown?'unknown':'failure')}><b>{title}</b><small>{choices.find(choice => choice.id===record.demo.demo)?.title} · {record.demo.demo==='equipment'?'EQ-001':scenarios.find(value => value.snapshot_id===record.demo.snapshot_id)?.title ?? record.demo.snapshot_id} · {record.demo.mode==='brain'?'官方大脑路径':'直接执行路径'}</small></div>
        {completed && rows.length>0 && <>
          <div className="runtime-result-summary">{record.demo.demo==='order_group'?<><b>{result?.output?.analysis?.feasible?'共同需求已满足':'共同需求存在缺口'}</b><span>{rows.some(row=>row.transfer_blocked)?'跨层通道停用，备料仍受阻':'跨层备料按工具返回单独核对'}</span></>:<><b>需求 {rows[0].demand} · 可用 {rows[0].available} · 缺口 {rows[0].shortage}</b><span>{rows[0].name} / {rows[0].material_id}</span></>}</div>
          {record.demo.demo==='legacy_contract' && <div className="runtime-conversion">输入 {version} / state <span>→</span> 输出 1.0.0 / factory_state · 实际转换见右侧轨迹</div>}
          <div className="table-scroll"><table><thead><tr><th>物料</th><th>需求</th><th>可用</th><th>缺口</th><th>跨层备料</th></tr></thead><tbody>{rows.map(row => <tr key={row.material_id}><td><b>{row.name}</b><small>{row.material_id} · {row.unit}</small></td><td>{row.demand}</td><td>{row.available}</td><td className={row.shortage?'shortage':''}>{row.shortage}</td><td className={row.transfer_blocked?'shortage':''}>{row.transfer_quantity}{row.transfer_blocked?' · 受阻':''}</td></tr>)}</tbody></table></div>
        </>}
        {completed && record.demo.demo==='equipment' && <div className="runtime-equipment"><b>{result?.output?.entity_id}</b><span>{({idle:'空闲',running:'运行中',maintenance:'检修中',offline:'离线'})[result?.output?.status as string]}</span><p>{result?.output?.requires_attention?'需要人工关注设备状态':'当前状态无需额外关注'}</p><small>没有执行启停或调度操作</small></div>}
        {result?.error && <div className="runtime-error"><b>{result.error.error_code}</b><p>{result.error.message}</p><small>{unknown?'未取得最终结果，请查询执行记录；此处不判定执行失败。':'错误来自 Runtime，执行编号和错误轨迹一并保留。'}</small></div>}
        {result?.output?.narrative && <details className="runtime-raw"><summary>官方模型解释 · 数量以工具返回为准</summary><p className="runtime-narrative">{result.output.narrative}</p></details>}
        <dl className="runtime-refs"><dt>任务编号</dt><dd>{record.request.task_id}</dd><dt>执行编号</dt><dd>{record.request.execution_id}</dd></dl>
        <div className="runtime-record-actions"><button disabled={querying} onClick={() => void query()}>{querying?'正在查询…':'查询这次执行'}</button><a href={'/api/v1/runtime/executions/'+record.request.execution_id+'/download'} download>导出完整记录 ↗</a></div>
        {queryNote && <p className="runtime-query-note" role="status">{queryNote}</p>}
        <details className="runtime-raw"><summary>查看标准输入与原始返回</summary><pre>{JSON.stringify(record,null,2)}</pre></details>
      </>}
    </section><div className="runtime-side"><section className="runtime-trace"><div className="section-head"><h2>真实执行轨迹</h2><span>{traces.length} 条</span></div>
      {traces.length===0?<p className="help">执行后显示能力、插件版本、时间与结果。轨迹来自本次 Runtime 返回。</p>:traces.map((trace,index) => <details key={trace.trace_id} className="runtime-trace-row">
        <summary><span>{String(index+1).padStart(2,'0')}</span><div><b>{capabilityNames[trace.capability.capability_id] ?? trace.capability.capability_id}</b><small>{trace.plugin_id} · v{trace.plugin_version}</small></div><em className={trace.status==='COMPLETED'?'ok':'bad'}>{trace.status==='COMPLETED'?'完成':'失败'}</em></summary>
        <div><p>{time(trace.start)} → {time(trace.end)} · {Math.max(0,new Date(trace.end).getTime()-new Date(trace.start).getTime())} ms</p><small>{trace.capability.capability_id} / {trace.capability.version}</small><pre>{JSON.stringify(trace.error ?? trace.result,null,2)}</pre></div>
      </details>)}
    </section><section className="runtime-catalog"><div className="section-head"><h2>已注册能力</h2><span>{catalog?.catalog.capabilities?.length ?? 0} 项</span></div>
      {catalog?.catalog.capabilities?.map(capability => <div key={capability.capability_id}><b>{capabilityNames[capability.capability_id] ?? capability.capability_id}</b><small>{capability.capability_id} · v{capability.version}</small></div>)}
    </section></div></div>
    {history.length>0 && <section className="runtime-session-history"><div className="section-head"><h2>本页执行记录</h2><span>当前页面会话 · {history.length} 次</span></div>{history.map(value => <button key={value.request.execution_id} disabled={busy} onClick={() => view(value)}>
      <b>{choices.find(choice => choice.id===value.demo.demo)?.title}</b><span>{value.demo.demo==='equipment'?({idle:'空闲',running:'运行中',maintenance:'检修中',offline:'离线'})[value.demo.equipment_status]:scenarios.find(item=>item.snapshot_id===value.demo.snapshot_id)?.title}</span><em>{value.result.status==='COMPLETED'?'完成':value.result.status==='FAILED'?'失败':'未确认'}</em><small>{value.request.execution_id.slice(-12)}</small>
    </button>)}</section>}
    <p className="runtime-boundary">这是本轮 Runtime 的临时交付展示入口。运行记录查询保留在 Runtime 当前进程；完整平台 Task 持久化、两位学弟的模块和三方联合验收仍待接入。</p>
  </div>;
}
