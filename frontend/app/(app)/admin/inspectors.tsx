import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import {
  fetchSlaughterhouses,
  fetchInspectors,
  createInspector,
} from "../../../src/api/admin";
import { Ionicons } from "@expo/vector-icons";

export default function AdminInspectors() {
  const [slaughterhouses, setSlaughterhouses] = useState([]);
  const [inspectors, setInspectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [selectedSlaughterhouseId, setSelectedSlaughterhouseId] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      const [sh, ins] = await Promise.all([
        fetchSlaughterhouses(),
        fetchInspectors(),
      ]);
      setSlaughterhouses(sh || []);
      setInspectors(ins || []);
    } catch (e) {
      setError("Erreur lors du chargement des données");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleSubmit = async () => {
    if (!email.trim() || !password.trim() || !selectedSlaughterhouseId) {
      setError("Email, mot de passe et abattoir sont obligatoires");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await createInspector({
        email: email.trim(),
        password: password.trim(),
        role: "inspector",
        slaughterhouse_id: selectedSlaughterhouseId,
      });
      setInspectors((prev) => [created, ...prev]);
      setEmail("");
      setPassword("");
      setSelectedSlaughterhouseId(null);
    } catch (e) {
      setError("Erreur lors de la création de l'inspecteur");
    } finally {
      setSaving(false);
    }
  };

  const renderInspector = ({ item }) => {
    const shName = slaughterhouses.find((s: any) => s.id === item.slaughterhouse_id)?.name;
    return (
      <View style={styles.item}>
        <View style={{ flex: 1 }}>
          <Text style={styles.itemTitle}>{item.email}</Text>
          {shName && (
            <Text style={styles.itemSubtitle}>Abattoir: {shName}</Text>
          )}
        </View>
      </View>
    );
  };

  const renderSlaughterhouseChip = (item: any) => {
    const selected = item.id === selectedSlaughterhouseId;
    return (
      <TouchableOpacity
        key={item.id}
        style={[styles.chip, selected && styles.chipSelected]}
        onPress={() =>
          setSelectedSlaughterhouseId(selected ? null : item.id)
        }
      >
        <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
          {item.name}
        </Text>
      </TouchableOpacity>
    );
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.container}>
        <Text style={styles.title}>Inspecteurs</Text>

        <View style={styles.form}>
          <Text style={styles.sectionTitle}>Nouvel inspecteur</Text>

          <Text style={styles.label}>Email</Text>
          <TextInput
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            placeholder="inspecteur@exemple.com"
          />

          <Text style={styles.label}>Mot de passe</Text>
          <View style={styles.passwordRow}>
            <TextInput
              style={[styles.input, { flex: 1, marginBottom: 0 }]}
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!showPassword}
              placeholder="Mot de passe"
            />
            <TouchableOpacity
              onPress={() => setShowPassword((prev) => !prev)}
              style={styles.eyeButton}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Ionicons
                name={showPassword ? "eye-off-outline" : "eye-outline"}
                size={20}
                color="#666"
              />
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>Abattoir</Text>
          <View style={styles.chipContainer}>
            {slaughterhouses.map((item: any) => renderSlaughterhouseChip(item))}
          </View>

          {error && <Text style={styles.error}>{error}</Text>}

          <TouchableOpacity
            style={styles.primaryButton}
            onPress={handleSubmit}
            disabled={saving}
          >
            {saving ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <Text style={styles.primaryButtonText}>Créer</Text>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.listContainer}>
          <Text style={styles.sectionTitle}>Liste des inspecteurs</Text>
          {loading ? (
            <ActivityIndicator style={{ marginTop: 16 }} />
          ) : (
            <FlatList
              data={inspectors}
              keyExtractor={(item: any) => item.id}
              renderItem={renderInspector}
              contentContainerStyle={{ paddingBottom: 24 }}
            />
          )}
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: "#C62828",
    marginBottom: 12,
  },
  form: {
    backgroundColor: "#F9F9F9",
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 8,
  },
  label: {
    fontSize: 14,
    color: "#333",
    marginBottom: 4,
  },
  input: {
    borderWidth: 1,
    borderColor: "#DDD",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: 10,
    fontSize: 14,
  },
  chipContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginBottom: 10,
  },
  chip: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#C62828",
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 4,
    marginBottom: 4,
  },
  chipSelected: {
    backgroundColor: "#C62828",
  },
  chipText: {
    color: "#C62828",
    fontSize: 13,
  },
  chipTextSelected: {
    color: "#FFF",
  },
  error: {
    color: "#C62828",
    marginBottom: 8,
  },
  primaryButton: {
    backgroundColor: "#C62828",
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    alignItems: "center",
  },
  primaryButtonText: {
    color: "#FFF",
    fontWeight: "600",
  },
  listContainer: {
    flex: 1,
  },
  item: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#EEE",
  },
  itemTitle: {
    fontSize: 16,
    fontWeight: "500",
  },
  itemSubtitle: {
    fontSize: 13,
    color: "#666",
  },
});
