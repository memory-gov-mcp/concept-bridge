const domains: Readonly<Record<string, string>> = {
  materials: "材料科学",
  materials_science: "材料科学",
  biology: "生物学",
  chemistry: "化学",
  medicine: "医学",
  physics: "物理学",
  algorithms: "计算机科学",
  computer_science: "计算机科学",
  unknown: "领域待定",
};

export function domainLabel(domain: string) {
  return Object.hasOwn(domains, domain) ? domains[domain] : domain;
}
