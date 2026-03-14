/** Shared image style options for style picker dropdowns. */
export const IMAGE_STYLE_GROUPS = [
  {
    label: 'Photography',
    options: [
      { value: 'photorealistic', label: 'Photorealistic' },
      { value: 'editorial', label: 'Editorial' },
      { value: 'documentary', label: 'Documentary' },
      { value: 'cinematic', label: 'Cinematic' },
      { value: 'food-photo', label: 'Food Photo' },
      { value: 'product', label: 'Product' },
      { value: 'lifestyle', label: 'Lifestyle' },
      { value: 'lo-fi', label: 'Lo-Fi' },
    ],
  },
  {
    label: 'Illustration',
    options: [
      { value: 'illustration', label: 'Illustration' },
      { value: 'hand-drawn', label: 'Hand-Drawn' },
      { value: 'anime', label: 'Anime' },
      { value: 'cartoon', label: 'Cartoon' },
      { value: 'watercolor', label: 'Watercolor' },
      { value: 'pixel-art', label: 'Pixel Art' },
      { value: 'risograph', label: 'Risograph' },
    ],
  },
  {
    label: '3D & Futuristic',
    options: [
      { value: '3d-render', label: '3D Render' },
      { value: 'futuristic', label: 'Futuristic' },
      { value: 'retro-futurism', label: 'Retro-Futurism' },
    ],
  },
  {
    label: 'Graphic Design',
    options: [
      { value: 'bold-minimal', label: 'Bold Minimal' },
      { value: 'maximalist', label: 'Maximalist' },
      { value: 'neo-brutalist', label: 'Neo-Brutalist' },
      { value: 'mixed-media', label: 'Mixed Media' },
      { value: 'flat-design', label: 'Flat Design' },
      { value: 'glitch', label: 'Glitch' },
    ],
  },
  {
    label: 'Mood / Aesthetic',
    options: [
      { value: 'cozy', label: 'Cozy' },
      { value: 'nature', label: 'Nature' },
      { value: 'luxury', label: 'Luxury' },
      { value: 'energetic', label: 'Energetic' },
      { value: 'nostalgic', label: 'Nostalgic' },
      { value: 'dreamy', label: 'Dreamy' },
    ],
  },
  {
    label: 'Industry',
    options: [
      { value: 'corporate', label: 'Corporate' },
      { value: 'craftsmanship', label: 'Craftsmanship' },
      { value: 'data-viz', label: 'Data Viz' },
      { value: 'ugc', label: 'UGC' },
    ],
  },
] as const
