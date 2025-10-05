# Birds with Friends - Frontend

A React-based frontend application for the Birds with Friends project, providing an interactive interface to view live bird feed, create stories, manage characters, and handle notifications.

## Features

### 🎥 Live Feed Page
- Embedded Cornell Lab Bird Cam stream
- Real-time snapshot carousel
- Quick story generation
- Recent activity summary

### 📖 Stories Management
- Create new stories with comprehensive form
- Episode timeline management
- Story type selection (Educational, Adventure, etc.)
- Character and age group targeting
- Scheduled publishing

### 🐦 Character Management
- View and edit bird character profiles
- Archetype assignment and management
- Character merging capabilities
- Name assignment and updates

### 🔔 Notifications
- Email notification preferences
- Web Push notification subscription
- SMS notifications (coming soon)
- Test notification functionality

## Tech Stack

- **React 18** - Modern React with hooks and functional components
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **React Query** - Data fetching and state management
- **React Hook Form** - Form handling with validation
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls

## Prerequisites

- Node.js 18+ and npm
- Running backend API server (see main project README)

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Setup

Create a `.env.local` file in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_VAPID_PUBLIC_KEY=your-vapid-public-key-here
```

### 3. Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### 4. Production Build

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── public/                 # Static assets
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── LoadingSpinner.tsx
│   │   ├── Navbar.tsx
│   │   ├── SnapshotCarousel.tsx
│   │   └── StoryCreateModal.tsx
│   ├── pages/            # Main page components
│   │   ├── CharactersPage.tsx
│   │   ├── LivePage.tsx
│   │   ├── NotificationsPage.tsx
│   │   └── StoriesPage.tsx
│   ├── services/         # API integration
│   │   └── api.ts
│   ├── types/           # TypeScript definitions
│   │   └── api.ts
│   ├── App.tsx          # Main app component
│   └── main.tsx         # Entry point
├── package.json
├── tailwind.config.js   # TailwindCSS configuration
├── tsconfig.json        # TypeScript configuration
└── vite.config.ts       # Vite configuration
```

## API Integration

The frontend integrates with the Birds with Friends backend API through a centralized service layer:

### Key Endpoints
- `GET /snapshots` - Recent bird snapshots
- `POST /stories` - Create new stories
- `GET /characters` - Character management
- `POST /notifications/subscribe` - Notification preferences
- `GET /aggregator/summary` - Activity summary

### Error Handling
- Automatic retry for failed requests
- Toast notifications for user feedback
- Graceful degradation when services are unavailable

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript compiler check

## Key Components

### StoryCreateModal
Comprehensive story creation interface with:
- Tabbed form layout (Basic Info, Characters, Settings)
- Multi-select controls for characters and age groups
- Form validation with Yup schema
- Episode scheduling capabilities

### SnapshotCarousel
Displays recent bird activity with:
- Auto-rotating image carousel
- Timestamp display
- Loading states and error handling

### CharactersPage
Character management interface featuring:
- Grid layout of character cards
- Edit modal for character details
- Bulk selection and merge functionality
- Archetype management

### NotificationsPage
Notification preference management with:
- Email notification toggles
- Web Push subscription handling
- SMS setup (coming soon)
- Test notification functionality

## Development Guidelines

### Code Style
- Use TypeScript for all new components
- Follow React Hook patterns
- Use TailwindCSS utility classes
- Implement proper error boundaries

### API Integration
- Use React Query for data fetching
- Implement loading and error states
- Cache responses appropriately
- Handle offline scenarios

### Form Handling
- Use React Hook Form with Yup validation
- Provide clear field validation messages
- Implement proper submission states

## Troubleshooting

### Common Issues

**Module not found errors:**
```bash
npm install @types/node @types/react @types/react-dom
```

**API connection issues:**
- Verify backend server is running on port 8000
- Check CORS configuration in backend
- Confirm proxy settings in `vite.config.ts`

**Build errors:**
```bash
npm run type-check
npm run lint
```

### Browser Support
- Modern browsers with ES2015+ support
- Chrome 70+, Firefox 65+, Safari 12+
- Web Push requires HTTPS in production

## Deployment

### Production Build
1. Set production environment variables
2. Run `npm run build`
3. Serve the `dist` folder with a web server
4. Configure proper HTTPS for Web Push notifications

### Docker Deployment
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0"]
```

## Contributing

1. Follow the established code structure
2. Add proper TypeScript types for new features
3. Include proper error handling and loading states
4. Test API integrations thoroughly
5. Update this README for new features

## Future Enhancements

- [ ] SMS notification implementation
- [ ] Real-time WebSocket integration for live updates
- [ ] Progressive Web App (PWA) features
- [ ] Mobile app using React Native
- [ ] Advanced story editing features
- [ ] Character relationship mapping
- [ ] Story analytics and insights