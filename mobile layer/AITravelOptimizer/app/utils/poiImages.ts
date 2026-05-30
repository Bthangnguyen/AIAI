/**
 * POI Real Images Mapper
 * Maps Hue POI names to real, high-quality, stunning Unsplash images.
 */

export function getPOIImage(poiName: string = "", category: string = ""): string {
  const name = poiName.toLowerCase().trim();
  const cat = category.toLowerCase().trim();

  // 🏛️ Di tích, lăng tẩm hoàng cung
  if (
    name.includes("đại nội") ||
    name.includes("hoàng thành") ||
    name.includes("kinh thành") ||
    name.includes("ngọ môn") ||
    name.includes("thái hòa")
  ) {
    return "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("thiên mụ")) {
    return "https://images.unsplash.com/photo-1571401835393-8c882e254a8b?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("tự đức") || name.includes("khiêm lăng")) {
    return "https://images.unsplash.com/photo-1588668214407-6ea9a6d8c272?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("khải định") || name.includes("ứng lăng")) {
    return "https://images.unsplash.com/photo-1578662996442-48f60103fc96?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("minh mạng") || name.includes("hiếu lăng")) {
    return "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("an định")) {
    return "https://images.unsplash.com/photo-1549887534-1541e9326642?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("quốc học")) {
    return "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("gia long")) {
    return "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("đồng khánh")) {
    return "https://images.unsplash.com/photo-1588668214407-6ea9a6d8c272?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("thiệu trị")) {
    return "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("hòn chén")) {
    return "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&q=80&w=1200";
  }

  // 🌉 Cầu & Sông & Địa danh thiên nhiên
  if (name.includes("trường tiền") || name.includes("tràng tiền")) {
    return "https://images.unsplash.com/photo-161642285623-13ff0162193c?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("sông hương") || name.includes("hương giang")) {
    return "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("vọng cảnh")) {
    return "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("ngự bình")) {
    return "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("thuận an")) {
    return "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("thủy tiên")) {
    return "https://images.unsplash.com/photo-1603890037267-56d6c0b3c285?auto=format&fit=crop&q=80&w=1200";
  }
  if (name.includes("thanh toàn")) {
    return "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?auto=format&fit=crop&q=80&w=1200";
  }

  // 🍜 Ẩm thực & Chợ & Cafe
  if (name.includes("đông ba")) {
    return "https://images.unsplash.com/photo-1555921015-5532091f6026?auto=format&fit=crop&q=80&w=1200";
  }
  if (
    name.includes("bún bò") ||
    name.includes("bánh bèo") ||
    name.includes("bánh lọc") ||
    name.includes("bánh khoái") ||
    name.includes("bà đỏ") ||
    name.includes("chè") ||
    name.includes("hẻm") ||
    name.includes("cơm hến") ||
    name.includes("ẩm thực") ||
    name.includes("quán") ||
    name.includes("nhà hàng")
  ) {
    return "https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?auto=format&fit=crop&q=80&w=1200";
  }
  if (
    name.includes("cà phê") ||
    name.includes("cafe") ||
    name.includes("muối") ||
    name.includes("vy gia") ||
    name.includes("vĩ dạ")
  ) {
    return "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=1200";
  }

  // Phân loại theo category làm dự phòng
  if (cat === "food") {
    return "https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?auto=format&fit=crop&q=80&w=1200";
  }
  if (cat === "cafe") {
    return "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=1200";
  }
  if (cat === "culture" || cat === "art") {
    return "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?auto=format&fit=crop&q=80&w=1200";
  }
  if (cat === "nature" || cat === "adventure") {
    return "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&q=80&w=1200";
  }

  return "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?auto=format&fit=crop&q=80&w=1200";
}
