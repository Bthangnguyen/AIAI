import React, { useState } from 'react';
import { Modal, View, Text, TextInput, Pressable, StyleSheet, FlatList } from 'react-native';
import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

interface AddPlaceModalProps {
  visible: boolean;
  onClose: () => void;
  onAddPlaces: (placeIds: string[]) => void;
}

export const AddPlaceModal: React.FC<AddPlaceModalProps> = ({ visible, onClose, onAddPlaces }) => {
  const [chat, setChat] = useState('');
  const [results, setResults] = useState<{id: string, name: string}[]>([]);
  const [selected, setSelected] = useState<string[]>([]);

  const handleSearch = () => {
    // Mock NLP search behavior
    if (chat.toLowerCase().includes('bún bò')) {
      setResults([{ id: 'mock-1', name: 'Bún Bò Huế' }]);
    } else {
      setResults([
        { id: 'mock-2', name: 'Quán Chay Liên Hoa' },
        { id: 'mock-3', name: 'Cafe Muối Chú Long' }
      ]);
    }
  };

  const toggleSelect = (id: string) => {
    setSelected(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.header}>
            <Text style={styles.title}>Thêm địa điểm (AI)</Text>
            <Pressable onPress={onClose}><Text style={styles.closeBtn}>✕</Text></Pressable>
          </View>
          
          <TextInput 
            placeholder="VD: Thêm bún bò..." 
            value={chat} 
            onChangeText={setChat} 
            style={styles.input} 
          />
          <Pressable style={styles.searchBtn} onPress={handleSearch}>
            <Text style={styles.btnText}>Tìm kiếm</Text>
          </Pressable>
          
          <FlatList 
            data={results}
            keyExtractor={item => item.id}
            contentContainerStyle={{ marginVertical: 10 }}
            renderItem={({item}) => {
              const isSelected = selected.includes(item.id);
              return (
                <Pressable 
                  onPress={() => toggleSelect(item.id)} 
                  style={[styles.resultItem, isSelected && styles.resultItemSelected]}
                >
                  <Text style={{ color: isSelected ? '#fff' : '#000' }}>{item.name}</Text>
                </Pressable>
              );
            }}
          />
          
          {selected.length > 0 && (
            <Pressable 
              style={styles.addBtn} 
              onPress={() => { onAddPlaces(selected); onClose(); }}
            >
              <Text style={styles.btnText}>Thêm {selected.length} điểm vào lộ trình</Text>
            </Pressable>
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: 'white', padding: 20, borderTopLeftRadius: 20, borderTopRightRadius: 20, minHeight: '60%' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 },
  title: { fontSize: 18, fontFamily: typography.primary.bold },
  closeBtn: { fontSize: 20, padding: 5 },
  input: { borderWidth: 1, borderColor: '#ddd', padding: 12, borderRadius: 8, marginBottom: 10, fontSize: 16 },
  searchBtn: { backgroundColor: colors.palette.figmaGrayDark, padding: 12, borderRadius: 8, alignItems: 'center' },
  addBtn: { backgroundColor: colors.tint, padding: 15, borderRadius: 8, alignItems: 'center', marginTop: 10 },
  btnText: { color: 'white', fontFamily: typography.primary.semiBold, fontSize: 16 },
  resultItem: { padding: 15, backgroundColor: '#f5f5f5', borderRadius: 8, marginBottom: 8 },
  resultItemSelected: { backgroundColor: colors.tint }
});
