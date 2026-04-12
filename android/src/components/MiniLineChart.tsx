import React from "react";
import { StyleSheet, View } from "react-native";
import Svg, { Circle, Path, Rect } from "react-native-svg";

import { palette } from "../theme";
import type { Dataset } from "../types";

type Props = {
  dataset: Dataset;
};

export function MiniLineChart({ dataset }: Props) {
  const width = 240;
  const height = 86;
  const pad = 8;
  const values = dataset.data.map((point) => point.y);
  const minValue = Math.min(...values);
  const maxValueRaw = Math.max(...values);
  const maxValue = maxValueRaw === minValue ? maxValueRaw + 1 : maxValueRaw;
  const xAt = (index: number) => {
    if (dataset.data.length === 1) {
      return width / 2;
    }
    return pad + (index / (dataset.data.length - 1)) * (width - pad * 2);
  };
  const yAt = (value: number) => pad + (1 - (value - minValue) / (maxValue - minValue)) * (height - pad * 2);
  const path = dataset.data
    .map((point, index) => `${index === 0 ? "M" : "L"} ${xAt(index).toFixed(2)} ${yAt(point.y).toFixed(2)}`)
    .join(" ");
  const lastIndex = dataset.data.length - 1;

  return (
    <View style={styles.wrap}>
      <Svg width={width} height={height}>
        <Rect x={0} y={0} width={width} height={height} rx={16} fill="#fff" />
        <Path d={path} fill="none" stroke={dataset.borderColor} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
        <Circle cx={xAt(lastIndex)} cy={yAt(dataset.data[lastIndex].y)} r={3.5} fill={dataset.borderColor} />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 8,
  },
});
