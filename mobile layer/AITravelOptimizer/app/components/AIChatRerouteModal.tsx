import React, { useState } from 'react';
import { Modal, View, Text, TextInput, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';
import { RerouteService } from '@/services/api/rerouteService';
import { ReRoutePayload } from '@/navigators/navigationTypes';

interface AIChatRerouteModalProps {
  visible: boolean;
  onClose: () => void;
  onConfirmReroute: (userState: ReRoutePayload['user_state']) => void;
}

const QUICK_TAGS = [
  { id: 'rain', label: '🌧️ Trời mưa', state: { weather: 'rain', wants_indoor: true } },
  { id: 'tired', label: '🥵 Đang mệt', state: { tired: true, wants_shorter_plan: true } },
  { id: 'hungry', label: '🍜 Đang đói', state: { hungry: true } },
  { id: 'chill', label: '☕ Muốn đi cafe', state: { wants_cafe: true } }
];

export const AIChatRerouteModal: React.FC<AIChatRerouteModalProps> = ({ visible, onClose, onConfirmReroute }) => {
  const [chat, setChat] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleAISubmit = async () => {
    if (!chat.trim()) return;
    setIsProcessing(true);
    try {
      const extractedState = await RerouteService.extractUserState(chat);
      onConfirmReroute(extractedState);
    } catch (e) {
      console.warn("AI extraction failed", e);
    } finally {
      setIsProcessing(false);
      setChat('');
      onClose();
    }
  };

  const handleQuickTag = (state: ReRoutePayload['user_state']) => {
    onConfirmReroute(state);
    onClose();
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.header}>
            <Text style={styles.title}>Tính toán lại lịch trình (AI)</Text>
            <Pressable onPress={onClose}><Text style={styles.closeBtn}>✕</Text></Pressable>
          </View>
          
          <Text style={styles.subtitle}>
            Bạn đang gặp vấn đề gì? Hãy kể cho AI nghe để lên lịch trình mới phù hợp hơn nhé!
          </Text>

          <TextInput 
            placeholder="VD: Mình mệt quá, đổi quán cafe nghỉ ngơi đi..." 
            value={chat} 
            onChangeText={setChat} 
            style={styles.input} 
            multiline
          />
          
          <Pressable 
            style={[styles.searchBtn, isProcessing && { opacity: 0.7 }]} 
            onPress={handleAISubmit}
            disabled={isProcessing}
          >
            {isProcessing ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.btnText}>Gửi cho AI 🪄</Text>
            )}
          </Pressable>

          <View style={styles.dividerContainer}>
            <View style={styles.divider} />
            <Text style={styles.dividerText}>Hoặc chọn nhanh (Khi Offline)</Text>
            <View style={styles.divider} />
          </View>

          <View style={styles.tagsContainer}>
            {QUICK_TAGS.map(tag => (
              <Pressable 
                key={tag.id} 
                style={styles.tagBtn} 
                onPress={() => handleQuickTag(tag.state)}
              >
                <Text style={styles.tagText}>{tag.label}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: 'white', padding: 20, borderTopLeftRadius: 20, borderTopRightRadius: 20, minHeight: '50%' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  title: { fontSize: 18, fontFamily: typography.primary.bold },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 15 },
  closeBtn: { fontSize: 20, padding: 5 },
  input: { borderWidth: 1, borderColor: '#ddd', padding: 12, borderRadius: 8, marginBottom: 15, fontSize: 16, minHeight: 80, textAlignVertical: 'top' },
  searchBtn: { backgroundColor: colors.tint, padding: 14, borderRadius: 8, alignItems: 'center' },
  btnText: { color: 'white', fontFamily: typography.primary.semiBold, fontSize: 16 },
  
  dividerContainer: { flexDirection: 'row', alignItems: 'center', marginVertical: 20 },
  divider: { flex: 1, height: 1, backgroundColor: '#eee' },
  dividerText: { marginHorizontal: 10, color: '#999', fontSize: 12 },
  
  tagsContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  tagBtn: { backgroundColor: '#f0f0f0', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20 },
  tagText: { color: '#333', fontSize: 14, fontFamily: typography.primary.medium }
});
