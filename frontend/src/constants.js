export const ROLES={admin:'运维主管',planner:'清洗计划员',viewer:'电站观察员'};
export const SURVEY_STATES={recorded:'待评估',evaluating:'评估中',assessed:'已评估',scheduled:'清洗中',retested:'已复测',closed:'已闭环',blocked:'需重试',stale:'清洗前旧读数'};
export const MISSION_STATES={draft:'待派工',dispatched:'执行中',retested:'待验收',accepted:'已验收',superseded:'旧计划已失效'};
export const ROAD_STATES={draft:'许可草稿',reserved:'时段已占位',paused:'封路暂停待改约',entered:'便道内',exited:'本班已出场',voided:'已释放'};
export const ROAD_LANE_STATES={open:'便道开放',closed:'便道封闭'};
export const ESTIMATE_SOURCES={model:'历史车次模型',supervisor:'主管估时',pending:'待估时'};
