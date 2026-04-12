import React from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";

import { palette, shadows } from "../theme";
import type { AnalysisSection } from "../types";
import { InteractiveLineChart } from "./InteractiveLineChart";
import { MiniBarChart } from "./MiniBarChart";
import { MiniLineChart } from "./MiniLineChart";

type Props = {
  analysis: AnalysisSection;
  index: number;
};

export function SectionCard({ analysis, index }: Props) {
  const mainDataset = analysis.datasets.find((dataset) => dataset.label === analysis.main_dataset_label) ?? analysis.datasets[0];

  return (
    <View style={styles.card}>
      <Text style={styles.sectionIndex}>Section {String(index + 1).padStart(2, "0")}</Text>
      <Text style={styles.title}>{analysis.title}</Text>
      <Text style={styles.headline}>{analysis.headline}</Text>
      <Text style={styles.body}>{analysis.insight}</Text>

      <View style={styles.chartPanel}>
        <Text style={styles.badge}>Primary history: {analysis.main_dataset_label}</Text>
        <InteractiveLineChart dataset={mainDataset} />
        <Text style={styles.note}>{analysis.chart_note}</Text>
      </View>

      {analysis.stats?.length ? (
        <View style={styles.statsRow}>
          {analysis.stats.map((stat) => (
            <View key={`${analysis.id}-${stat.label}`} style={styles.statCard}>
              <Text style={styles.statLabel}>{stat.label}</Text>
              <Text style={styles.statValue}>{stat.value}</Text>
            </View>
          ))}
        </View>
      ) : null}

      <View style={styles.supportWrap}>
        {analysis.support_charts.map((chart) => (
          <View key={`${analysis.id}-${chart.title}`} style={styles.supportCard}>
            <Text style={styles.supportTitle}>{chart.title}</Text>
            <Text style={styles.supportValue}>{chart.value}</Text>
            {chart.kind === "line" && chart.dataset ? <MiniLineChart dataset={chart.dataset} /> : null}
            {chart.kind === "bars" && chart.items ? <MiniBarChart items={chart.items} color={chart.color ?? palette.teal} /> : null}
            <Text style={styles.supportText}>{chart.subtext}</Text>
          </View>
        ))}
      </View>

      <View style={styles.sourcesWrap}>
        {analysis.sources.map((source) => (
          <Pressable key={`${analysis.id}-${source.table_id}`} style={styles.sourceChip} onPress={() => Linking.openURL(source.url)}>
            <Text style={styles.sourceKey}>{source.table_id}</Text>
            <Text style={styles.sourceText}>{source.last_modified_date}</Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.commentaryCard}>
        <Text style={styles.commentaryLabel}>Commentary</Text>
        <Text style={styles.commentaryText}>{analysis.commentary}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginTop: 16,
    backgroundColor: palette.paper,
    borderRadius: 28,
    padding: 18,
    borderWidth: 1,
    borderColor: palette.border,
    ...shadows.card,
  },
  sectionIndex: {
    fontSize: 11,
    letterSpacing: 1.4,
    textTransform: "uppercase",
    color: palette.muted,
    marginBottom: 6,
  },
  title: {
    fontSize: 30,
    lineHeight: 31,
    fontWeight: "700",
    color: palette.ink,
  },
  headline: {
    marginTop: 10,
    fontSize: 18,
    lineHeight: 22,
    fontWeight: "700",
    color: palette.teal,
  },
  body: {
    marginTop: 8,
    fontSize: 15,
    lineHeight: 22,
    color: palette.muted,
  },
  chartPanel: {
    marginTop: 16,
    backgroundColor: "#FFFDF7",
    borderRadius: 22,
    padding: 14,
    borderWidth: 1,
    borderColor: palette.borderSoft,
  },
  badge: {
    alignSelf: "flex-start",
    borderRadius: 999,
    borderWidth: 1,
    borderColor: palette.border,
    color: palette.muted,
    paddingHorizontal: 10,
    paddingVertical: 6,
    fontSize: 11,
    marginBottom: 10,
  },
  note: {
    marginTop: 8,
    fontSize: 13,
    lineHeight: 18,
    color: palette.muted,
  },
  statsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginTop: 14,
  },
  statCard: {
    flexBasis: "47%",
    backgroundColor: palette.panel,
    borderRadius: 18,
    padding: 12,
    borderWidth: 1,
    borderColor: palette.borderSoft,
  },
  statLabel: {
    fontSize: 11,
    color: palette.muted,
    letterSpacing: 1.2,
    textTransform: "uppercase",
    marginBottom: 8,
  },
  statValue: {
    fontSize: 19,
    lineHeight: 22,
    fontWeight: "700",
    color: palette.ink,
  },
  supportWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
    marginTop: 14,
  },
  supportCard: {
    flexBasis: "47%",
    backgroundColor: palette.panel,
    borderRadius: 20,
    padding: 14,
    borderWidth: 1,
    borderColor: palette.borderSoft,
  },
  supportTitle: {
    fontSize: 17,
    lineHeight: 20,
    fontWeight: "700",
    color: palette.ink,
  },
  supportValue: {
    marginTop: 6,
    fontSize: 14,
    lineHeight: 18,
    color: palette.teal,
    fontWeight: "700",
  },
  supportText: {
    marginTop: 10,
    fontSize: 13,
    lineHeight: 18,
    color: palette.muted,
  },
  sourcesWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginTop: 14,
  },
  sourceChip: {
    backgroundColor: palette.panel,
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: palette.borderSoft,
  },
  sourceKey: {
    fontSize: 11,
    letterSpacing: 1,
    textTransform: "uppercase",
    color: palette.muted,
  },
  sourceText: {
    marginTop: 4,
    fontSize: 13,
    color: palette.ink,
    fontWeight: "700",
  },
  commentaryCard: {
    marginTop: 14,
    backgroundColor: palette.panel,
    borderRadius: 20,
    padding: 14,
    borderWidth: 1,
    borderColor: palette.borderSoft,
    borderLeftWidth: 4,
    borderLeftColor: palette.teal,
  },
  commentaryLabel: {
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: "uppercase",
    color: palette.muted,
    marginBottom: 8,
  },
  commentaryText: {
    fontSize: 14,
    lineHeight: 20,
    color: palette.muted,
  },
});
