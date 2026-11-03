const labels: Readonly<Record<string, string>> = {
  inhibit: "抑制", promote: "促进", transport: "传输", transform: "转化",
  recognize: "识别", amplify: "放大", stabilize: "稳定", degrade: "降解",
  compete: "竞争", isolate: "隔离", trigger: "触发", regulate: "调节",
};

export function actionLabel(actionClass: string) {
  return Object.hasOwn(labels, actionClass) ? labels[actionClass] : actionClass;
}
