"""Simple comparator: fit sources separately, retain agreeing accepted planes.

No truth or path labels enter this baseline. Agreement is a repeatability check,
not proof against a persistent higher-order alias. Report medoid uncertainty;
never shrink it by treating shared surveys as independent measurements.
"""
import copy
import math
import numpy as np
from echosight.inference import infer_scene


def plane_difference(a,b):
    an=np.asarray(a['normal']);bn=np.asarray(b['normal']);dot=float(an@bn)
    sign=1 if dot>=0 else -1
    return float(np.degrees(np.arccos(np.clip(abs(dot),0,1)))),abs(float(a['offset_m'])-sign*float(b['offset_m']))


def independent_consensus(processed_sessions):
    separate=[];clusters=[]
    for i,item in enumerate(processed_sessions):
        result=infer_scene(item['session'],item['observations']);separate.append(result)
        for plane in result.get('surfaces',[]):
            eligible=[]
            for j,cluster in enumerate(clusters):
                if any(index==i for index,_ in cluster):continue
                distances=[plane_difference(plane,other) for _,other in cluster]
                if all(angle<=5 and distance<=.15 for angle,distance in distances):
                    eligible.append((sum(angle/5+distance/.15 for angle,distance in distances),j))
            if eligible:clusters[min(eligible)[1]].append((i,plane))
            else:clusters.append([(i,plane)])
    required=max(2,math.ceil(.75*len(processed_sessions)));surfaces=[]
    for cluster in clusters:
        if len(cluster)<required:continue
        scores=[sum(a/5+d/.15 for _,other in cluster for a,d in [plane_difference(plane,other)]) for _,plane in cluster]
        index=int(np.argmin(scores));surface=copy.deepcopy(cluster[index][1]);surface['surface_id']=f'consensus-{len(surfaces):03d}'
        surface['source_session_support']=[processed_sessions[i]['session']['session_id'] for i,_ in cluster]
        surface['uncertainty_semantics']='Single-source medoid uncertainty retained; shared calibration not averaged down.'
        surfaces.append(surface)
    return {'schema_version':'1.0','status':'partial' if surfaces else 'no_result','surfaces':surfaces,
        'diagnostics':[{'code':'independent_source_consensus','message':f'Requires geometrical agreement in {required} sources. Cannot reject an invariant higher-order alias.'}],
        'single_source_status':[r['status'] for r in separate],'hypotheses':[]}
