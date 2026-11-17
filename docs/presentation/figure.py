"""Draw exact processed response samples and actual support-hull triangles.
This synthetic room case is separate from the published measured ultrasound route.
All response samples are retained; projection uses a common affine projection and one uniform screen scale.
"""
from pathlib import Path
import json,html
P=Path(__file__).resolve().parent;d=json.loads((P/'twelve-view-result.json').read_text());f=json.loads((P/'five-view-result.json').read_text());o=d['observations'][0];r=o['response'];vals=r['values'];assert len(vals)==4225 and len(d['surfaces'])==6 and len(f['surfaces'])==0;assert f['status']=='ambiguous' and d['status']=='partial'
def make(mobile):
 W,H=(420,1230) if mobile else (1200,810);m=28 if mobile else 44;parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">','<title id="title">EchoSight: echoes support patches, not complete rooms</title>','<desc id="desc">One actual synthetic recording response with all 4,225 samples and five candidate echo delays. Twelve surveyed synthetic views yield six partial reflection-support hulls; five views remain ambiguous with no accepted patches. Neither plot establishes physical room accuracy.</desc>','<style>text{font-family:Arial,Helvetica,sans-serif;fill:#e6f2ea}.muted{fill:#b7cbbd}.accent{fill:#9bd68b}</style>',f'<rect width="{W}" height="{H}" fill="#0b1710"/>']
 def t(x,y,v,size=20,cls='',weight=400):parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" class="{cls}">{html.escape(v)}</text>')
 t(m,48,'EchoSight',28,weight=700)
 if mobile:t(m,104,'Echoes support patches.',30,weight=700);t(m,146,'Not complete rooms.',30,weight=700)
 else:t(m,116,'Echoes support patches. Not complete rooms.',44,weight=700)
 t(m,187 if mobile else 163,'Actual synthetic room-processing output',17,'muted')
 x,y,pw,ph=(57,260,330,220) if mobile else (75,270,515,275)
 t(m,227,'One processed response array',23,weight=700)
 def xy(i,v):time=1000*(r['start_delay_s']+i/r['sample_rate_hz']);return x+(time+5)/90*pw,y+ph-(v+.2)/.6*ph
 for value in [-.2,0,.2,.4]:
  yy=y+ph-(value+.2)/.6*ph;parts.append(f'<path d="M{x} {yy:.4f}H{x+pw}" stroke="#496451" stroke-width=".6"/>');t(x-31,yy+5,f'{value:g}',13,'muted')
 for v in [0,20,40,60,80]:t(x+(v+5)/90*pw-7,y+ph+22,str(v),13,'muted')
 path=' '.join(('M' if i==0 else'L')+f'{a:.5f},{b:.5f}' for i,(a,b) in enumerate(xy(i,v) for i,v in enumerate(vals)));parts.append(f'<path id="response" d="{path}" fill="none" stroke="#a4d892" stroke-width="1"/>')
 for candidate in o['candidates']:
  xx=x+(candidate['delay_s']*1000+5)/90*pw;parts.append(f'<path class="candidate" d="M{xx:.5f} {y}V{y+ph}" stroke="#b7cbbd" stroke-dasharray="3 5" stroke-width=".7"/>')
 t(m,y+ph+56,'Excess delay from direct arrival (ms)',16,'muted');t(m,y+ph+86,'Signed response; arbitrary amplitude units.',15,'muted')
 gx,gy,gw,gh=(28,660,364,260) if mobile else (666,270,490,290)
 t(gx,gy-28,'Reflection-support hulls',23,weight=700)
 proj=lambda p:(.8*p[0]-.5*p[1],.25*p[0]+.25*p[1]-.9*p[2]);vertices=[v for surf in d['surfaces'] for v in surf['vertices_m']];pv=[proj(v) for v in vertices];lo=[min(p[i] for p in pv) for i in (0,1)];hi=[max(p[i] for p in pv) for i in (0,1)];scale=min((gw-20)/(hi[0]-lo[0]),(gh-20)/(hi[1]-lo[1]))
 def pt(v):a,b=proj(v);return gx+10+(a-lo[0])*scale,gy+10+(b-lo[1])*scale
 colors=['#5a8e71','#8bad68','#8bb6a3','#749485','#abc68b','#688976']
 for j,surf in enumerate(d['surfaces']):
  for tri in surf['triangles']:
   points=' '.join(f'{a:.5f},{b:.5f}' for a,b in [pt(surf['vertices_m'][i]) for i in tri]);parts.append(f'<polygon class="support" points="{points}" fill="{colors[j]}" fill-opacity=".23" stroke="{colors[j]}" stroke-width="1.2"/>')
 t(gx,gy+gh+32,'Metres; common affine projection.',15,'muted');t(gx,gy+gh+61,'Support hulls are not physical wall edges.',15,'muted')
 if mobile:
  t(m,1047,'5 views: ambiguous, no supported patch.',18,'accent',700);t(m,1083,'12 views: partial, six supported patches.',18,'accent',700);t(m,1130,'Same first five WAVs. No physical validation.',16,'muted');t(m,1170,'Originals survive export; import reprocesses.',16,'muted')
 else:
  t(m,680,'Five views remain ambiguous; twelve views yield six partial support patches.',25,'accent',700);t(m,724,'The first five WAVs are identical. This is one controlled synthetic case, not a physical accuracy study.',19,'muted');t(m,770,'Original recordings stay intact across archive export and reprocessing. Published measured ultrasound remains a separate route.',17,'muted')
 parts.append('</svg>');return'\n'.join(parts)+'\n'
for n,m in [('echo-support',False),('echo-support-mobile',True)]:(P/(n+'.svg')).write_text(make(m))
