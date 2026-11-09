import React from "react";
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { StatusBar as ExpoStatusBar } from "expo-status-bar";

import reportData from "./src/data/reportData.json";
import { SectionCard } from "./src/components/SectionCard";
import { palette, shadows } from "./src/theme";
import type { ReportPayload } from "./src/types";

const payload = reportData as ReportPayload;

export default function App() {
  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safeArea}>
        <ExpoStatusBar style="dark" />
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.hero}>
            <Text style={styles.eyebrow}>Hong Kong C&SD Historical Monitor</Text>
            <Text style={styles.title}>HK Census, reworked for touch interaction.</Text>
            <Text style={styles.description}>
              This mobile app follows the same ten-section analysis as the local web report. Each section leads with an interactive
              historical chart and then adds smaller supporting graphics for context.
            </Text>

            <Pressable
              accessibilityRole="link"
              accessibilityLabel="Read the HK Census privacy policy"
              style={styles.privacyLink}
              onPress={() => Linking.openURL("https://vkcrystalgem.github.io/hkcensus_privacy_policy.html")}
            >
              <Text style={styles.privacyLinkText}>Privacy policy</Text>
            </Pressable>

            <View style={styles.summaryRow}>
              <View style={styles.summaryCard}>
                <Text style={styles.summaryLabel}>Analyses</Text>
                <Text style={styles.summaryValue}>{payload.sections.length}</Text>
              </View>
              <View style={styles.summaryCard}>
                <Text style={styles.summaryLabel}>Latest release</Text>
                <Text style={styles.summaryValue}>{payload.latest_release}</Text>
              </View>
            </View>

            <View style={styles.summaryRow}>
              <View style={styles.summaryCard}>
                <Text style={styles.summaryLabel}>Generated</Text>
                <Text style={styles.summaryValueSmall}>{payload.generated_at}</Text>
              </View>
              <View style={styles.summaryCard}>
                <Text style={styles.summaryLabel}>Namespace</Text>
                <Text style={styles.summaryValueSmall}>com.vkcrystalgem.hkcensus</Text>
              </View>
            </View>
          </View>

          {payload.sections.map((section, index) => (
            <SectionCard key={section.id} analysis={section} index={index} />
          ))}
        </ScrollView>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  content: {
    padding: 14,
    paddingBottom: 28,
  },
  hero: {
    backgroundColor: palette.paper,
    borderRadius: 28,
    padding: 20,
    borderWidth: 1,
    borderColor: palette.border,
    ...shadows.card,
  },
  eyebrow: {
    fontSize: 11,
    letterSpacing: 1.6,
    textTransform: "uppercase",
    color: palette.muted,
    marginBottom: 10,
  },
  title: {
    fontSize: 34,
    lineHeight: 36,
    fontWeight: "700",
    color: palette.ink,
    marginBottom: 12,
  },
  description: {
    fontSize: 15,
    lineHeight: 22,
    color: palette.muted,
  },
  privacyLink: {
    alignSelf: "flex-start",
    justifyContent: "center",
    minHeight: 44,
    marginTop: 4,
    paddingHorizontal: 4,
  },
  privacyLinkText: {
    color: palette.teal,
    fontSize: 14,
    textDecorationLine: "underline",
  },
  summaryRow: {
    flexDirection: "row",
    gap: 12,
    marginTop: 14,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: palette.panel,
    borderRadius: 18,
    padding: 14,
    borderWidth: 1,
    borderColor: palette.borderSoft,
  },
  summaryLabel: {
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: "uppercase",
    color: palette.muted,
    marginBottom: 8,
  },
  summaryValue: {
    fontSize: 22,
    lineHeight: 24,
    fontWeight: "700",
    color: palette.ink,
  },
  summaryValueSmall: {
    fontSize: 14,
    lineHeight: 18,
    fontWeight: "700",
    color: palette.ink,
  },
});

