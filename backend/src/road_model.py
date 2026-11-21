import json,hashlib,math
from functools import lru_cache
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
FEATURES=['load_liters','wet_road']
MIN_TRAIN_TRIPS=24
MIN_CONDITION_TRIPS=8
CONDITION_LABEL={False:'干路面',True:'湿路面'}

@lru_cache(maxsize=1)
def train_reference():
    source=Path(__file__).resolve().parents[1]/'fixtures/north_road_trips.json'
    raw=source.read_bytes();rows=json.loads(raw)
    rows=sorted(rows,key=lambda r:(r['trip_date'],r['trip_code']))
    dates=sorted({r['trip_date'] for r in rows})
    holdout_dates=set(dates[-max(1,math.ceil(len(dates)*.25)):])
    train=[r for r in rows if r['trip_date'] not in holdout_dates]
    test=[r for r in rows if r['trip_date'] in holdout_dates]
    matrix=lambda rs:np.array([[float(r['load_liters']),1.0 if r['wet_road'] else 0.0] for r in rs])
    target=lambda rs:np.array([float(r['duration_minutes']) for r in rs])
    model=RandomForestRegressor(n_estimators=100,max_depth=6,min_samples_leaf=2,random_state=42,n_jobs=1)
    model.fit(matrix(train),target(train))
    train_mae=float(mean_absolute_error(target(train),model.predict(matrix(train))))
    holdout_mae=float(mean_absolute_error(target(test),model.predict(matrix(test))))
    evidence={'reference_rows':len(rows),'train_rows':len(train),'holdout_rows':len(test),
        'holdout_dates':sorted(holdout_dates),'train_dates':sorted(set(dates)-holdout_dates),
        'train_mae_minutes':round(train_mae,4),'holdout_mae_minutes':round(holdout_mae,4),
        'feature_importance':dict(zip(FEATURES,model.feature_importances_.tolist())),
        'random_state':42,'sha256':hashlib.sha256(raw).hexdigest(),
        'method':'RandomForestRegressor / 100 trees / max_depth 6 / 按日期留出',
        'min_train_rows':MIN_TRAIN_TRIPS,'min_condition_rows':MIN_CONDITION_TRIPS,
        'features':FEATURES,'fixture':'north_road_trips.json'}
    return {'model':model,'evidence':evidence,'rows':rows,
        'train_dates':set(evidence['train_dates'])}

def summary():
    return train_reference()['evidence']

def estimate(load_liters,wet_road,supervisor_minutes=None):
    bundle=train_reference();evidence=dict(bundle['evidence'])
    rows=bundle['rows'];train_dates=bundle['train_dates']
    condition=bool(wet_road)
    condition_rows=sum(1 for r in rows if bool(r['wet_road'])==condition and r['trip_date'] in train_dates)
    model_minutes=max(5,math.ceil(float(bundle['model'].predict([[float(load_liters),1.0 if condition else 0.0]])[0])))
    enough=evidence['train_rows']>=MIN_TRAIN_TRIPS and condition_rows>=MIN_CONDITION_TRIPS
    evidence.update({'condition':CONDITION_LABEL[condition],'condition_train_rows':condition_rows,
        'model_minutes':model_minutes,'conditional_sample_sufficient':enough})
    model_note=(f"按日期留出：训练{evidence['train_rows']}条、留出{evidence['holdout_rows']}条，"
        f"留出MAE {evidence['holdout_mae_minutes']:.2f}分钟；{CONDITION_LABEL[condition]}训练样本{condition_rows}条。")
    if supervisor_minutes is not None:
        minutes=int(supervisor_minutes)
        reason='' if enough else f"（{CONDITION_LABEL[condition]}样本少于{MIN_CONDITION_TRIPS}条，模型估时仅供参考）"
        basis=f'主管估时{minutes}分钟{reason}；模型参考{model_minutes}分钟。{model_note}'
        evidence.update({'available':True,'fallback_reason':'' if enough else '样本不足，由主管估时'})
        return {'minutes':minutes,'source':'supervisor','requires_supervisor':False,'basis':basis,'evidence':evidence}
    if not enough:
        basis=(f'{CONDITION_LABEL[condition]}历史仅{condition_rows}条（少于{MIN_CONDITION_TRIPS}条），'
            f'或训练样本不足{MIN_TRAIN_TRIPS}条，模型估时不可靠，请主管估时。模型参考{model_minutes}分钟。')
        evidence.update({'available':False,'fallback_reason':'样本不足，由主管估时'})
        return {'minutes':None,'source':None,'requires_supervisor':True,'basis':basis,'evidence':evidence}
    basis=f'模型估时{model_minutes}分钟。{model_note}'
    evidence.update({'available':True,'fallback_reason':''})
    return {'minutes':model_minutes,'source':'model','requires_supervisor':False,'basis':basis,'evidence':evidence}
