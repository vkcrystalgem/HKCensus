import React from "react";
import { StyleSheet, View } from "react-native";
import Svg, { Line, Rect, Text as SvgText } from "react-native-svg";

import { palette } from "../theme";
import type { SupportBarItem } from "../types";

type Props = {
  items: SupportBarItem[];
  color: string;
};

export function MiniBarChart({ items, color }: Props) {
  const width = 240;
  const height = 126;
  const left = 20;
  const right = 18;
  const top = 18;
  const bottom = 34;
  const innerWidth = width - left - right;
  const innerHeight = height - top - bottom;
  const values = items.map((item) => item.value);
  const minValue = Math.min(0, ...values);
  const maxValueRaw = Math.max(0, ...values);
  const maxValue = maxValueRaw === minValue ? maxValueRaw + 1 : maxValueRaw;
  const baseline = top + (1 - (0 - minValue) / (maxValue - minValue)) * innerHeight;
  const gap = 10;
  const barWidth = Math.min(42, (innerWidth - gap * (items.length - 1)) / Math.max(items.length, 1));
  const totalWidth = items.length * barWidth + gap * (items.length - 1);
  const startX = left + (innerWidth - totalWidth) / 2;
  const yAt = (value: number) => top + (1 - (value - minValue) / (maxValue - minValue)) * innerHeight;

  return (
    <View style={styles.wrap}>
      <Svg width={width} height={height}>
        <Rect x={0} y={0} width={width} height={height} rx={16} fill="#fff" />
        <Line x1={left} y1={baseline} x2={width - right} y2={baseline} stroke="rgba(98,95,87,0.16)" strokeWidth={1} />
        {items.map((item, index) => {
          const x = startX + index * (barWidth + gap);
          const y = Math.min(yAt(item.value), baseline);
          const barHeight = Math.max(Math.abs(yAt(item.value) - baseline), 1.5);
          const labelY = item.value >= 0 ? y - 6 : y + barHeight + 12;
          return (
            <React.Fragment key={`${item.label}-${index}`}>
              <Rect x={x} y={y} width={barWidth} height={barHeight} rx={8} fill={item.color ?? color} opacity={0.82} />
              <SvgText x={x + barWidth / 2} y={labelY} fontSize={10} fill={palette.ink} textAnchor="middle">
                {item.display}
              </SvgText>
              <SvgText x={x + barWidth / 2} y={height - 10} fontSize={10} fill={palette.muted} textAnchor="middle">
                {item.label}
              </SvgText>
            </React.Fragment>
          );
        })}
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 8,
  },
});
