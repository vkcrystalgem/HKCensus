import reportData from "../data/reportData.json";

describe("report data payload", () => {
  it("contains the same ten sections as the web analysis", () => {
    expect(reportData.sections).toHaveLength(10);
  });

  it("ships the expected section ids", () => {
    const ids = reportData.sections.map((section) => section.id);
    expect(ids).toEqual([
      "population-level",
      "population-growth-components",
      "ageing",
      "fertility",
      "household-structure",
      "household-income",
      "labour-force",
      "unemployment",
      "gdp",
      "inflation"
    ]);
  });

  it("provides a main dataset label and support charts for each section", () => {
    for (const section of reportData.sections) {
      expect(section.main_dataset_label).toBeTruthy();
      expect(Array.isArray(section.support_charts)).toBe(true);
      expect(section.support_charts.length).toBeGreaterThan(0);
    }
  });
});
