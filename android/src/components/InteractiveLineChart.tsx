import React, { useState } from "react";
import { LayoutChangeEvent, PanResponder, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, G, Line, Path, Rect, Text as SvgText } from "react-native-svg";

import { EVENT_MARKERS } from "../data/events";
import { palette } from "../theme";
import type { Dataset } from "../types";
import { buildLineChartModel, chartTooltipBounds, compactNumber, formatHoverValue } from "../utils/chart";

type Props = {
  dataset: Dataset;
  height?: number;
};

export function InteractiveLineChart({ dataset, height = 286 }: Props) {
  const [width, setWidth] = useState(320);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const model = buildLineChartModel(dataset, width, height, EVENT_MARKERS);
  const activePoint = activeIndex === null ? null : model.points[activeIndex];

  const updateActive = (locationX: number) => {
    let nearestIndex = 0;
    let nearestDistance = Number.MAX_VALUE;
    model.points.forEach((point, index) => {
      const distance = Math.abs(point.x - locationX);
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestIndex = index;
      }
    });
    setActiveIndex(nearestIndex);
  };

  const panResponder = PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: () => true,
    onPanResponderGrant: (event) => updateActive(event.nativeEvent.locationX),
    onPanResponderMove: (event) => updateActive(event.nativeEvent.locationX),
    onPanResponderRelease: () => setActiveIndex(null),
    onPanResponderTerminate: () => setActiveIndex(null),
  });

  const onLayout = (event: LayoutChangeEvent) => {
    const nextWidth = Math.max(1, Math.floor(event.nativeEvent.layout.width));
    if (nextWidth !== width) {
      setWidth(nextWidth);
    }
  };

  const tooltip = activePoint ? chartTooltipBounds(activePoint.x, activePoint.y, width, height) : null;
  const peakPoint = model.points[model.peakIndex];

  return (
    <View style={styles.container} onLayout={onLayout}>
      <Text style={[styles.datasetLabel, { color: dataset.borderColor }]}>{dataset.label}</Text>
      <View>
        <Svg width={width} height={height}>
          <Rect x={0} y={0} width={width} height={height} rx={24} fill={palette.panel} />

          {model.yTicks.map((tick) => (
            <G key={`y-${tick.y}`}>
              <Line
                x1={model.chartLeft}
                y1={tick.y}
                x2={model.chartRight}
                y2={tick.y}
                stroke="rgba(98,95,87,0.14)"
                strokeWidth={1}
              />
              <SvgText x={model.chartLeft - 8} y={tick.y + 4} fontSize={11} fill={palette.muted} textAnchor="end">
                {tick.label}
              </SvgText>
            </G>
          ))}

          {model.events.map((event) => (
            <G key={`${event.short}-${event.x}`}>
              <Line
                x1={event.x}
                y1={model.chartTop}
                x2={event.x}
                y2={model.chartBottom}
                stroke={palette.red}
                strokeOpacity={0.34}
                strokeDasharray="5 4"
                strokeWidth={1.2}
              />
            </G>
          ))}

          <Path d={model.areaPath} fill={dataset.borderColor} opacity={0.12} />
          <Path d={model.linePath} fill="none" stroke={dataset.borderColor} strokeWidth={3.2} strokeLinejoin="round" strokeLinecap="round" />

          <Circle cx={peakPoint.x} cy={peakPoint.y} r={4.5} fill={dataset.borderColor} />

          {model.xTicks.map((tick) => (
            <G key={`${tick.label}-${tick.x}`}>
              <Line
                x1={tick.x}
                y1={model.chartBottom}
                x2={tick.x}
                y2={model.chartBottom + 6}
                stroke="rgba(98,95,87,0.22)"
                strokeWidth={1}
              />
              <SvgText x={tick.x} y={height - 14} fontSize={11} fill={palette.muted} textAnchor="middle">
                {tick.label}
              </SvgText>
            </G>
          ))}

          {activePoint && tooltip ? (
            <G>
              <Line
                x1={activePoint.x}
                y1={model.chartTop}
                x2={activePoint.x}
                y2={model.chartBottom}
                stroke={dataset.borderColor}
                strokeOpacity={0.6}
                strokeDasharray="4 4"
                strokeWidth={1.5}
              />
              <Circle cx={activePoint.x} cy={activePoint.y} r={5} fill={dataset.borderColor} stroke={palette.panel} strokeWidth={2} />
              <Rect
                x={tooltip.left}
                y={tooltip.top}
                width={tooltip.boxWidth}
                height={tooltip.boxHeight}
                rx={12}
                fill="rgba(255,253,247,0.98)"
                stroke="rgba(98,95,87,0.18)"
              />
              <SvgText x={tooltip.left + 10} y={tooltip.top + 17} fontSize={11} fill={palette.ink}>
                {activePoint.label}
              </SvgText>
              <SvgText x={tooltip.left + 10} y={tooltip.top + 32} fontSize={12} fill={dataset.borderColor} fontWeight="700">
                {formatHoverValue(activePoint.value)}
              </SvgText>
            </G>
          ) : null}
        </Svg>
        <View style={StyleSheet.absoluteFill} {...panResponder.panHandlers} />
      </View>
      <Text style={[styles.peak, { color: dataset.borderColor }]}>
        Peak {compactNumber(peakPoint.value)} · {peakPoint.label}
      </Text>
      {model.events.length ? (
        <Text style={styles.events}>Dashed markers: {model.events.map((event) => event.label).join(" · ")}</Text>
      ) : null}
      <Text style={styles.helper}>Touch and drag across the chart to inspect values.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: "100%",
  },
  datasetLabel: {
    marginBottom: 6,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "700",
  },
  peak: {
    marginTop: 4,
    fontSize: 12,
    lineHeight: 17,
    fontWeight: "600",
  },
  events: {
    marginTop: 6,
    fontSize: 11,
    lineHeight: 16,
    color: palette.red,
  },
  helper: {
    marginTop: 8,
    fontSize: 12,
    lineHeight: 17,
    color: palette.muted,
  },
});
