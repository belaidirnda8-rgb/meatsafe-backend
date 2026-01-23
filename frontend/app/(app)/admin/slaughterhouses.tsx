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
  createSlaughterhouse,
  updateSlaughterhouse,
} from "../../../src/api/admin";

export default function AdminSlaughterhouses() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null);

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [location, setLocation] = useState("");

  const load = async () => {
    try {
      setLoading(true);
      const data = await fetchSlaughterhouses();
      setItems(data || []);
    } catch (e) {
      setError("Erreur lors du chargement des abattoirs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const resetForm = () => {
    setEditing(null);
    setName("");
    setCode("");
    setLocation("");
  };

  const handleEdit = (item: any) => {
    setEditing(item);
    setName(item.name || "");
    setCode(item.code || "");
    setLocation(item.location || "");
  };

  const handleSubmit = async () => {
    if (!name.trim() || !code.trim()) {
      setError("Nom et code sont obligatoires");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (editing && editing.id) {
        const updated = await updateSlaughterhouse(editing.id, {
          name: name.trim(),
          code: code.trim(),
          location: location.trim() || null,
        });
        setItems((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      } else {
        const created = await createSlaughterhouse({
          name: name.trim(),
          code: code.trim(),
          location: location.trim() || undefined,
        });
        setItems((prev) => [created, ...prev]);
      }
      resetForm();
    } catch (e) {
      setError("Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  };

  const renderItem = ({ item }: { item: any }) => (
    <TouchableOpacity style={styles.item} onPress={() => handleEdit(item)}>
      <View style={{ flex: 1 }}>
        <Text style={styles.itemTitle}>{item.name}</Text>
        <Text style={styles.itemSubtitle}>Code: {item.code}</Text>
        {item.location ? (
          <Text style={styles.itemSubtitle}>Lieu: {item.location}</Text>
        ) : null}
      </View>
      <Text style={styles.editText}>Modifier</Text>
    </TouchableOpacity>
  );

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.container}>
        <Text style={styles.title}>Abattoirs</Text>

        <View style={styles.form}>
          <Text style={styles.sectionTitle}>
            {editing ? "Modifier un abattoir" : "Nouvel abattoir"}
          </Text>

          <Text style={styles.label}>Nom</Text>
          <TextInput
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="Nom de l'abattoir"
          />

          <Text style={styles.label}>Code</Text>
          <TextInput
            style={styles.input}
            value={code}
            onChangeText={setCode}
            placeholder="Code interne"
          />

          <Text style={styles.label}>Localisation (optionnel)</Text>
          <TextInput
            style={styles.input}
            value={location}
            onChangeText={setLocation}
            placeholder="Ville, adresse, ..."
          />

          {error && <Text style={styles.error}>{error}</Text>}

          <View style={styles.formButtons}>
            {editing && (
              <TouchableOpacity style={styles.secondaryButton} onPress={resetForm}>
                <Text style={styles.secondaryButtonText}>Annuler</Text>
              </TouchableOpacity>
            )}

            <TouchableOpacity
              style={styles.primaryButton}
              onPress={handleSubmit}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color="#FFF" />
              ) : (
                <Text style={styles.primaryButtonText}>
                  {editing ? "Enregistrer" : "Créer"}
                </Text>
              )}
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.listContainer}>
          <Text style={styles.sectionTitle}>Liste des abattoirs</Text>
          {loading ? (
            <ActivityIndicator style={{ marginTop: 16 }} />
          ) : (
            <FlatList
              data={items}
              keyExtractor={(item: any) => item.id}
              renderItem={renderItem}
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
  error: {
    color: "#C62828",
    marginBottom: 8,
  },
  formButtons: {
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
    marginTop: 4,
  },
  primaryButton: {
    backgroundColor: "#C62828",
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    marginLeft: 8,
  },
  primaryButtonText: {
    color: "#FFF",
    fontWeight: "600",
  },
  secondaryButton: {
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: "#C62828",
  },
  secondaryButtonText: {
    color: "#C62828",
    fontWeight: "500",
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
  editText: {
    color: "#C62828",
    fontWeight: "600",
  },
});
