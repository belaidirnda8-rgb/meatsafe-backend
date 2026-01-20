import React from "react";
import { View, Text, StyleSheet } from "react-native";

export default function InspectorHome() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Liste des saisies (à implémenter)</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  text: {
    fontSize: 16,
  },
});
