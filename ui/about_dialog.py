"""
“关于 QTTrigrs”对话框：分页展示程序信息、署名致谢，以及 TRIGRS / TopoIndex
全部参数的说明（对照 USGS 官方文档与官方输入文件里的说明行）。

内容以 HTML 常量保存，渲染进 ``QTextBrowser``，因此可以自由排版表格。
"""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "QTTrigrs"
APP_VERSION = "1.0.0"

ABOUT_HTML = f"""
<style>
  body {{ font-size: 10pt; }}
  h2 {{ margin-bottom: 2px; }}
  h3 {{ margin-top: 16px; margin-bottom: 4px; }}
  code {{ background: #f2f2f2; padding: 0 2px; }}
  .sub {{ color: #666; }}
</style>
<h2>{APP_NAME}</h2>
<p class="sub">TRIGRS（含 TopoIndex）独立桌面程序 · PyQt5 界面 · 不依赖 QGIS · 版本 {APP_VERSION}</p>

<h3>这是什么</h3>
<p>
本程序把 <b>USGS TRIGRS</b> 与 <b>TopoIndex</b> 两个模型从 DizaiGIS4 里抽出来，
做成一个独立的桌面小工具：界面用 PyQt5，栅格直接从磁盘选取，输入输出文件仍是官方
<code>tr_in.txt</code> / <code>tpx_in.txt</code> 格式，可以和原版程序互相打开。
</p>

<h3>致敬与致谢</h3>
<p>
本程序的<b>全部算法与输入/输出格式都来自官方程序</b>，代码只是把求解部分重新实现成
Fortran 内核、把界面改成独立程序。原始模型与算法版权归原作者所有，特此郑重致谢：
</p>
<ul>
  <li><b>TRIGRS</b> —— <i>Transient Rainfall Infiltration and Grid-Based Regional
      Slope-Stability Model</i>。<br>
      作者：<b>Rex L. Baum</b>、William Z. Savage、Jonathan W. Godt
      （U.S. Geological Survey）。<br>
      参考版本：官方 TRIGRS 2.1（2010）。本程序完全对齐其求解流程与参数含义。</li>
  <li><b>TopoIndex</b> —— <i>Topographic Indexing and flow distribution factors for
      routing runoff through Digital Elevation Models</i>。<br>
      作者：<b>Rex L. Baum</b>（U.S. Geological Survey）。<br>
      参考版本：官方 TopoIndex 1.0.15；输入文件的说明行与版本号均按官方原文保留。</li>
</ul>
<p>
USGS 的软件属于美国联邦政府作品，为<b>公有领域（public domain）</b>，可自由使用与再分发。
感谢 USGS 长期公开这两个模型与文档，本程序才得以实现。
</p>

<h3>本程序相对官方程序做了什么</h3>
<ul>
  <li><b>求解内核</b>：TRIGRS 力学求解与 TopoIndex 的排序/坡度因子计算全部用 Fortran
      重新实现，经 <code>numpy.f2py</code> 编译成 <code>.pyd</code> 扩展，在<b>进程内后台线程</b>
      运行；内核标记为 <code>threadsafe</code>，调用期间释放 GIL，界面不会卡死。</li>
  <li><b>栅格 IO</b>：改用 <b>rasterio</b> 读写 GeoTIFF / ASCII Grid（不使用 GDAL Python 绑定）。</li>
  <li><b>界面</b>：从 QGIS 插件改成独立 PyQt5 程序，栅格直接从磁盘选择，不再依赖 QGIS 工程图层。</li>
  <li><b>兼容性</b>：输入文件说明行、参数顺序、输出文件命名都与官方一致；额外的图层绑定信息
      写在文件末尾的 <code>#</code> 注释块里，官方程序读取时会自动忽略。</li>
</ul>

<h3>技术栈</h3>
<ul>
  <li>Python 3.12 · PyQt5 · numpy · scipy · rasterio</li>
  <li>Fortran 内核：MinGW-w64 gfortran + numpy.f2py（Meson / Ninja 后端），
      gfortran 运行时 DLL 随程序放在 <code>lib/</code></li>
</ul>

<h3>怎么用</h3>
<ol>
  <li>先在 <b>TopoIndex</b> 页选 DEM（流向可选）→ 运行，生成径流汇流文件并自动回填；</li>
  <li>再到 <b>TRIGRS</b> 页选坡度/高程等栅格、填参数 → 检查参数 → 开始计算；</li>
  <li><b>输入文件预览</b>页可以随时检查将写出的 <code>tr_in.txt</code> / <code>tpx_in.txt</code>。</li>
</ol>
<p class="sub">具体每个参数的含义见右侧各“参数说明”页。</p>
"""

TOPOINDEX_HTML = """
<style>
  body {{ font-size: 10pt; }}
  h3 {{ margin-top: 14px; margin-bottom: 4px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #d0d0d0; padding: 3px 6px; vertical-align: top; }}
  th {{ background: #f2f2f2; text-align: left; }}
  code {{ background: #f2f2f2; padding: 0 2px; }}
  .note {{ color: #666; }}
</style>
<h3>TopoIndex 参数（tpx_in.txt）</h3>
<p class="note">
官方输入文件是“说明行 + 取值行”交替的 12 组，程序按行序读取，说明行只作注释。
界面上的字段与下表中的参数一一对应。
</p>
<table>
  <tr><th style="width:16%">参数</th><th style="width:46%">含义</th><th>取值 / 说明</th></tr>
  <tr><td><code>heading</code></td><td>工程说明（Name of project）</td>
      <td>任意文本，最长 255 字符；仅作标识，不影响计算。</td></tr>
  <tr><td><code>aif</code></td><td>流向栅格的编码方案（Flow-direction numbering scheme）</td>
      <td><b>1 = ESRI D8</b>（取值 1/2/4/8/16/32/64/128）；<br>
          <b>2 = TopoIndex</b>（取值 1–9）。<br>
          <span class="note">务必与你的流向栅格实际编码一致：选 1 时程序会把 ESRI 编码
          换算成 1–9；选 2 时按 1–9 原样使用。选错会算错流向。</span></td></tr>
  <tr><td><code>pwr</code></td><td>坡度指数（Exponent），控制坡面径流如何分配给下游单元</td>
      <td><b>&gt; 20</b>：退化为 D8，全部水量走最陡的下游单元；<br>
          <b>= 0</b>：在全部下游单元间<b>均匀</b>分配；<br>
          <b>= 1</b>：按<b>坡度大小</b>成比例分配；<br>
          <b>0 &lt; pwr ≤ 20</b>：按坡度的 <code>pwr</code> 次幂分配（幂律，指数越大越集中在最陡处）；<br>
          <b>&lt; 0</b>：启用 <b>D-infinity</b> 方法（把流向按角度分配到相邻两个单元）。</td></tr>
  <tr><td><code>itmax</code></td><td>单元顺序修正的最大迭代次数（Number of iterations）</td>
      <td>整数。<code>correct_order</code> 每迭代一次把排序沿流路推进一格，
          需要的次数≈<b>最长流路的单元数</b>。<br>
          <span class="note">小网格 10 就够；几百米到几公里、几百万单元的大 DEM
          往往需要上千次（例如 1769×4031 的网格实测需要 ≈1280）。次数不够时会提示
          “未收敛”，并且不会生成后续产物。</span></td></tr>
  <tr><td><code>demfil</code></td><td>DEM 高程栅格文件名（Name of elevation grid file）</td>
      <td>ASCII Grid 或 GeoTIFF。必须是<b>有效单元编号</b>的来源，也是输出栅格的模板
          （继承其行列数、仿射变换与投影）。</td></tr>
  <tr><td><code>dirfil</code></td><td>流向栅格文件名（Name of direction grid）</td>
      <td>可选。留空时程序只输出 <code>TIgrid_size.txt</code>（网格尺寸参数），不做后续分析。</td></tr>
  <tr><td><code>op(1)</code></td><td>是否保存 <b>D8 下游邻居单元列表</b>
      （Save listing of D8 downslope neighbor cells）</td>
      <td>T/F。产物：<code>TIdsneiList_&lt;suffix&gt;.txt</code>。</td></tr>
  <tr><td><code>op(2)</code></td><td>是否保存 <b>D8 下游邻居单元栅格</b>
      （Save grid of D8 downslope neighbor cells）</td>
      <td>T/F。产物：<code>TIdscelGrid_&lt;suffix&gt;.asc|.tif</code>，
          每个像元的值是它最陡下游单元的编号（TRIGRS 的 <code>nxtfil</code>）。</td></tr>
  <tr><td><code>op(3)</code></td><td>是否保存 <b>单元计算顺序栅格</b>
      （Save cell index number grid）</td>
      <td>T/F。产物：<code>TIcelindxGrid_&lt;suffix&gt;.asc|.tif</code>，
          值越小越先参与径流演算。</td></tr>
  <tr><td><code>op(4)</code></td><td>是否保存 <b>单元编号与索引号列表</b>
      （Save list of cell number and corresponding index number）</td>
      <td>T/F。产物：<code>TIcelindxList_&lt;suffix&gt;.txt</code>，
          两列：单元编号、计算顺序（TRIGRS 的 <code>ndxfil</code>）。</td></tr>
  <tr><td><code>op(5)</code></td><td>是否保存 <b>重编码后的流向栅格</b>
      （Save flow-direction grid remapped from ESRI to TopoIndex）</td>
      <td>T/F。仅在 <code>aif=1</code> 时有意义。产物：
          <code>TIflodirGrid_&lt;suffix&gt;.asc|.tif</code>（1–9 编码）。</td></tr>
  <tr><td><code>op(6)</code></td><td>是否保存 <b>山脊栅格</b>
      （Save grid of points on ridge crests）</td>
      <td>T/F。产物：<code>TIridge_crest_&lt;suffix&gt;.asc|.tif</code>。
          <span class="note"><code>pwr &lt; 0</code>（D-infinity）时无法计算山脊，
          此时即使勾选也不会生成。</span></td></tr>
  <tr><td><code>lspars</code></td><td>山脊是否<b>稀疏</b>输出（Sparse T / dense F）</td>
      <td>T = 稀疏（内部阈值 6），F = 密集（阈值 5）。影响山脊栅格的判定。</td></tr>
  <tr><td><code>suffix</code></td><td>输出文件名标识（ID code for output files）</td>
      <td>不超过 8 字符，会拼进所有产物文件名，便于区分不同方案。</td></tr>
</table>

<h3>输出产物一览</h3>
<table>
  <tr><th style="width:34%">文件</th><th>说明</th></tr>
  <tr><td><code>TIdsneiList_&lt;suffix&gt;.txt</code></td><td>D8 下游邻居列表（对应 op(1)）</td></tr>
  <tr><td><code>TIdscelGrid_&lt;suffix&gt;.asc|.tif</code></td><td>D8 下游单元编号栅格（op(2)，即 TRIGRS 的 nxtfil）</td></tr>
  <tr><td><code>TIcelindxGrid_&lt;suffix&gt;.asc|.tif</code></td><td>单元计算顺序栅格（op(3)）</td></tr>
  <tr><td><code>TIcelindxList_&lt;suffix&gt;.txt</code></td><td>单元编号 ↔ 计算顺序列表（op(4)，即 ndxfil）</td></tr>
  <tr><td><code>TIflodirGrid_&lt;suffix&gt;.asc|.tif</code></td><td>重编码流向栅格（op(5)）</td></tr>
  <tr><td><code>TIridge_crest_&lt;suffix&gt;.asc|.tif</code></td><td>山脊栅格（op(6)，需 pwr ≥ 0）</td></tr>
  <tr><td><code>TIdscelList_&lt;suffix&gt;.txt</code></td><td>全部下游受体单元列表（TRIGRS 的 dscfil，总是生成）</td></tr>
  <tr><td><code>TIwfactorList_&lt;suffix&gt;.txt</code></td><td>径流权重因子列表（TRIGRS 的 wffil，总是生成）</td></tr>
  <tr><td><code>TIgrid_size.txt</code></td><td>网格尺寸参数：<code>imax nrow ncol nwf</code>（有效单元数、行列数、下游单元总数）</td></tr>
</table>
<p class="note">
栅格产物只写 <code>.asc</code> 或 <code>.tif</code>（由“栅格输出格式”选择）。列表类产物
（<code>*List*.txt</code>、<code>*snei*.txt</code>）本来就是纯文本，始终为 <code>.txt</code>。
</p>
"""

TRIGRS_HTML = """
<style>
  body {{ font-size: 10pt; }}
  h3 {{ margin-top: 14px; margin-bottom: 4px; }}
  h4 {{ margin: 10px 0 2px 0; color: #333; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #d0d0d0; padding: 3px 6px; vertical-align: top; }}
  th {{ background: #f2f2f2; text-align: left; }}
  code {{ background: #f2f2f2; padding: 0 2px; }}
  .note {{ color: #666; }}
</style>
<h3>TRIGRS 参数（tr_in.txt）</h3>
<p class="note">
参数名与官方说明行保持原文一致，顺序也与官方 <code>tr_in.txt</code> 相同。角度类参数在
界面填<b>度</b>，写文件/送入内核前会换算成弧度（与官方一致）。
</p>

<h4>1. 程序控制参数</h4>
<table>
  <tr><th style="width:16%">参数</th><th style="width:46%">含义</th><th>取值 / 说明</th></tr>
  <tr><td><code>title</code></td><td>工程名称（Name of project）</td><td>任意文本，最长 255 字符。</td></tr>
  <tr><td><code>tx</code></td><td>时间步倍数</td>
      <td>把每个降雨时段再细分成 <code>tx</code> 个时间步，越小越细。非饱和模型会按
          最小输出间隔自动增大 <code>tx</code>。</td></tr>
  <tr><td><code>nmax</code></td><td>求解压力水头的最大迭代次数</td>
      <td>整数。迭代不收敛时会给出提示。</td></tr>
  <tr><td><code>mmax</code></td><td>竖向最大分层数</td>
      <td>有限深度求解器在竖直方向允许的最大层数。</td></tr>
  <tr><td><code>zones</code></td><td>土壤分区数</td>
      <td>与 <code>zonfil</code> 的属性分区数一致；下面土壤参数表要填 <code>zones</code> 行。</td></tr>
</table>

<h4>2. 模拟控制参数</h4>
<table>
  <tr><th style="width:16%">参数</th><th style="width:46%">含义</th><th>取值 / 说明</th></tr>
  <tr><td><code>nzs</code></td><td>竖向分片数（每层细分数）</td><td>有限深度求解的竖直离散数。</td></tr>
  <tr><td><code>zmin</code></td><td>最小计算深度 (m)</td><td>竖直离散的最小厚度，默认 0.001。</td></tr>
  <tr><td><code>uww</code></td><td>水的重度 (N/m³)</td><td>默认 9.8e3。</td></tr>
  <tr><td><code>nper</code></td><td>降雨时段数</td><td>下面的 <code>cri</code> / <code>rifil</code> 要有 <code>nper</code> 项，
      <code>capt</code> 要有 <code>nper+1</code> 项。</td></tr>
  <tr><td><code>t</code></td><td>模拟总时长 (s)</td><td>默认 18000。</td></tr>
</table>

<h4>3. 初始条件参数</h4>
<table>
  <tr><th style="width:16%">参数</th><th style="width:46%">含义</th><th>取值 / 说明</th></tr>
  <tr><td><code>zmax</code></td><td>最大深度 (m)</td>
      <td>填<b>负值</b>表示“改读 <code>zfil</code> 栅格”；界面选了 zfil 时此标量被忽略。</td></tr>
  <tr><td><code>depth</code></td><td>初始地下水位深度 (m)</td>
      <td>填<b>负值</b>表示“改读 <code>depfil</code> 栅格”。</td></tr>
  <tr><td><code>rizero</code></td><td>初始入渗率 (m/s)</td>
      <td>填<b>负值</b>表示“改读 <code>rizerofil</code> 栅格”。</td></tr>
  <tr><td><code>slomin</code></td><td>最小坡度角 (°)</td><td>小于该坡度的单元按该值处理，默认 0。</td></tr>
  <tr><td><code>slomax</code></td><td>最大坡度角 (°)</td><td>大于该坡度的单元按该值处理，默认 90。</td></tr>
</table>

<h4>4. 土壤分区参数（每行 8 个值，共 <code>zones</code> 行）</h4>
<table>
  <tr><th style="width:16%">列</th><th>含义</th></tr>
  <tr><td><code>cohesion</code></td><td>粘聚力 c (Pa)</td></tr>
  <tr><td><code>phi</code></td><td>内摩擦角 φ (°)（内部换算成弧度）</td></tr>
  <tr><td><code>uws</code></td><td>土体重度 γs (N/m³)</td></tr>
  <tr><td><code>diffus</code></td><td>水力扩散系数 D (m²/s)</td></tr>
  <tr><td><code>K-sat</code></td><td>饱和导水率 Ks (m/s)</td></tr>
  <tr><td><code>Theta-sat</code></td><td>饱和含水率 θs</td></tr>
  <tr><td><code>Theta-res</code></td><td>残余含水率 θr</td></tr>
  <tr><td><code>Alpha</code></td><td>Gardner 参数 α (1/m)</td></tr>
</table>
<p class="note">单位与官方 TRIGRS 手册一致（SI）。分区编号与 <code>zonfil</code> 栅格的属性值对应。</p>

<h4>5. 降雨参数</h4>
<table>
  <tr><th style="width:16%">参数</th><th style="width:46%">含义</th><th>取值 / 说明</th></tr>
  <tr><td><code>cri(i)</code></td><td>第 i 时段的降雨强度 (m/s)</td>
      <td>共 <code>nper</code> 项。填<b>负值</b>表示该时段改读对应的 <code>rifil(i)</code> 栅格。</td></tr>
  <tr><td><code>capt(i)</code></td><td>时段边界时刻 (s)</td>
      <td>共 <code>nper+1</code> 项，必须单调递增。</td></tr>
  <tr><td><code>rifil(i)</code></td><td>第 i 时段的降雨强度栅格</td>
      <td>可选；与 <code>cri(i)</code> 二选一。</td></tr>
</table>

<h4>6. 栅格输入（从磁盘选择）</h4>
<table>
  <tr><th style="width:16%">参数</th><th style="width:46%">含义</th><th>取值 / 说明</th></tr>
  <tr><td><code>slofil</code></td><td>坡度角栅格</td><td>单位度或弧度需与官方约定一致，程序按官方方式处理。</td></tr>
  <tr><td><code>elevfil</code></td><td>高程栅格</td><td>用于水位面/深度换算。</td></tr>
  <tr><td><code>zonfil</code></td><td>属性分区栅格</td><td>值与第 4 节土壤参数行号对应。</td></tr>
  <tr><td><code>zfil</code></td><td>最大深度栅格</td><td>替代标量 <code>zmax</code>。</td></tr>
  <tr><td><code>depfil</code></td><td>初始地下水位深度栅格</td><td>替代标量 <code>depth</code>。</td></tr>
  <tr><td><code>rizerofil</code></td><td>初始入渗率栅格</td><td>替代标量 <code>rizero</code>。</td></tr>
</table>

<h4>7. 径流汇流文件（一般由 TopoIndex 产物自动回填）</h4>
<table>
  <tr><th style="width:16%">参数</th><th style="width:46%">含义</th><th>取值 / 说明</th></tr>
  <tr><td><code>nxtfil</code></td><td>D8 下游单元编号栅格</td><td>对应 TopoIndex 的 <code>TIdscelGrid_*</code>。</td></tr>
  <tr><td><code>ndxfil</code></td><td>径流计算顺序单元列表</td><td>对应 <code>TIcelindxList_*</code>。</td></tr>
  <tr><td><code>dscfil</code></td><td>全部下游受体单元列表</td><td>对应 <code>TIdscelList_*</code>。</td></tr>
  <tr><td><code>wffil</code></td><td>径流权重因子列表</td><td>对应 <code>TIwfactorList_*</code>。</td></tr>
</table>
<p class="note">四个文件齐全且 <code>TIgrid_size.txt</code> 存在时才会做径流演算；否则跳过该步骤。</p>

<h4>8. 输出选项</h4>
<table>
  <tr><th style="width:16%">参数</th><th style="width:46%">含义</th><th>取值 / 说明</th></tr>
  <tr><td><code>folder</code></td><td>输出文件夹</td><td>结果栅格/列表的存放目录，不存在会报错。</td></tr>
  <tr><td><code>suffix</code></td><td>输出文件名标识</td><td>拼进所有结果文件名。</td></tr>
  <tr><td><code>rodoc</code></td><td>保存径流栅格</td><td>T/F。产物 <code>TRrunoffPer*</code>。</td></tr>
  <tr><td><code>outp(2)</code></td><td>保存<b>最小安全系数</b>栅格</td><td>T/F。产物 <code>TRfsmin*</code>。</td></tr>
  <tr><td><code>outp(3)</code></td><td>保存<b>最小安全系数对应深度</b>栅格</td><td>T/F。产物 <code>TRzfmin*</code>。</td></tr>
  <tr><td><code>outp(4)</code></td><td>保存<b>最小安全系数处压力水头</b>栅格</td><td>T/F。产物 <code>TRpmin*</code>。</td></tr>
  <tr><td><code>outp(1)</code></td><td>保存<b>计算的地下水位</b>栅格</td>
      <td>T/F，后接 <code>depth</code> 或 <code>eleva</code> 选择输出“埋深”还是“高程”。</td></tr>
  <tr><td><code>outp(5)</code></td><td>保存<b>实际入渗率</b>栅格</td><td>T/F。产物 <code>TRinfilratPer*</code>。</td></tr>
  <tr><td><code>outp(6)</code></td><td>保存<b>非饱和区基底通量</b>栅格</td><td>T/F。</td></tr>
  <tr><td><code>flag</code></td><td>压力水头 / 安全系数<b>列表输出</b>模式</td>
      <td>
        <code>-1</code> Z-P-Fs 列表；<code>-2</code> 详细 Z-P-Fs；<code>-3</code> Z-P-Fs-饱和度；<br>
        <code>-4</code> 完整 ijz；<code>-5</code> 降采样 ijz；<code>-6</code> 稀疏 ijz；<br>
        <code>-7</code> 完整 xmdv；<code>-8</code> 降采样 xmdv；<code>-9</code> 稀疏 xmdv；<code>0</code> 不输出。<br>
        <span class="note">当前的 Fortran 内核已接通 <code>flag -1…-6</code>；
        <code>-7…-9</code>（xmdv）与 DizaiGIS4 原有行为一致，尚未实现。</span>
      </td></tr>
  <tr><td><code>spcg</code></td><td>降采样间隔</td><td>配合 <code>-5</code> / <code>-8</code> 使用。</td></tr>
  <tr><td><code>nout</code></td><td>输出次数</td><td>与 <code>tsav</code> 配对。</td></tr>
  <tr><td><code>tsav</code></td><td>输出时刻 (s)，多个用逗号分隔</td><td>在这些时刻保存结果。</td></tr>
  <tr><td><code>lskip</code></td><td>跳过其它时间步</td><td>T = 只在 <code>tsav</code> 时刻求解输出，省时间。</td></tr>
  <tr><td><code>lany</code></td><td>使用可填充孔隙度解析解</td><td>T/F。</td></tr>
  <tr><td><code>llus</code></td><td>估算上升地下水位区的正压力水头</td><td>T/F。</td></tr>
  <tr><td><code>lps0</code></td><td>取 <code>psi0 = -1/alpha</code></td>
      <td>T = 用 <code>-1/α</code>；F = 用默认值 <code>psi0 = 0</code>。</td></tr>
  <tr><td><code>outp(8)</code></td><td>记录质量平衡结果</td><td>T/F。</td></tr>
  <tr><td><code>flowdir</code></td><td>流向选项</td>
      <td><code>gener</code>（一般）、<code>slope</code>（沿坡向）、<code>hydro</code>（水文）三选一。</td></tr>
  <tr><td><code>bkgrof</code></td><td>零降雨期计入稳态背景通量</td>
      <td>T = 加上稳态背景入渗，避免降雨停止后比初始条件还干。</td></tr>
  <tr><td><code>lasc</code></td><td>输出栅格扩展名</td>
      <td>T = <code>.asc</code>（ASCII Grid）；F = <code>.tif</code>（GeoTIFF）。</td></tr>
  <tr><td><code>lpge0</code></td><td>计算安全系数时忽略负压力水头</td><td>仅饱和入渗情形，T/F。</td></tr>
  <tr><td><code>igcapf</code></td><td>忽略毛细带水高度</td><td>非饱和入渗情形，T/F。</td></tr>
</table>

<h4>9. SCOOPS 深层压力水头估计（ijz 输出）</h4>
<table>
  <tr><th style="width:16%">参数</th><th style="width:46%">含义</th><th>取值 / 说明</th></tr>
  <tr><td><code>deepz</code></td><td>地表以下深度 (m)</td>
      <td>正值启用；填<b>负值</b>取消该选项（界面默认 -50.0 即关闭）。</td></tr>
  <tr><td><code>deepwat</code></td><td>压力选项</td>
      <td><code>zero</code> / <code>flow</code> / <code>hydr</code> / <code>relh</code> 四选一。</td></tr>
</table>

<h3>主要输出文件</h3>
<table>
  <tr><th style="width:34%">文件</th><th>说明</th></tr>
  <tr><td><code>TRfsmin&lt;suffix&gt;</code></td><td>整个模拟期内最小安全系数栅格</td></tr>
  <tr><td><code>TRzfmin&lt;suffix&gt;</code></td><td>最小安全系数出现处的深度栅格</td></tr>
  <tr><td><code>TRpmin&lt;suffix&gt;</code></td><td>最小安全系数处的压力水头栅格</td></tr>
  <tr><td><code>TRwtab&lt;suffix&gt;</code></td><td>计算的地下水位（埋深或高程）</td></tr>
  <tr><td><code>TRrunoffPer&lt;n&gt;&lt;suffix&gt;</code></td><td>第 n 时段径流栅格</td></tr>
  <tr><td><code>TRinfilratPer&lt;n&gt;&lt;suffix&gt;</code></td><td>第 n 时段实际入渗率栅格</td></tr>
  <tr><td><code>TRzpf&lt;suffix&gt;.txt</code></td><td>Z-P-Fs 等列表输出（由 <code>flag</code> 决定）</td></tr>
  <tr><td><code>TrigrsLog.txt</code></td><td>运行日志</td></tr>
</table>
"""


class _HtmlDialog(QDialog):
    """只读 HTML 对话框（署名致谢与参数说明共用）。"""

    def __init__(self, title: str, html: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 660)

        browser = QTextBrowser(self)
        browser.setOpenExternalLinks(True)
        browser.setHtml(html)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(browser)
        layout.addWidget(buttons)


def show_about(parent: QWidget | None = None) -> None:
    """“关于 QTTrigrs”：程序简介与官方作者署名致谢。"""
    _HtmlDialog(f"关于 {APP_NAME}", ABOUT_HTML, parent).exec_()


def show_topoindex_params(parent: QWidget | None = None) -> None:
    """“TopoIndex 参数说明”：tpx_in.txt 全部参数与产物。"""
    _HtmlDialog("TopoIndex 参数说明", TOPOINDEX_HTML, parent).exec_()


def show_trigrs_params(parent: QWidget | None = None) -> None:
    """“TRIGRS 参数说明”：tr_in.txt 全部参数与输出文件。"""
    _HtmlDialog("TRIGRS 参数说明", TRIGRS_HTML, parent).exec_()
