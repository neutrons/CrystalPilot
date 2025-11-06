// @ts-check
// `@type` JSDoc annotations allow editor autocompletion and type checking
// (when paired with `@ts-check`).
// There are various equivalent ways to declare your Docusaurus config.
// See: https://docusaurus.io/docs/api/docusaurus-config

import {themes as prismThemes} from 'prism-react-renderer';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'CrystalPilot',
  tagline: 'CrystalPilot Documentation',
  favicon: 'img/favicon.ico',

  // Set the production url of your site here
  url: 'https://calvera.ornl.gov',
  baseUrl: '/',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
//          routeBasePath: '/', // Serve the docs at the site's root
          sidebarPath: './sidebars.js',
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      // Replace with your project's social card
      image: 'img/docusaurus-social-card.jpg',
      navbar: {
        title: 'CrystalPilot',
        logo: {
          alt: 'CrystalPilot Logo',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: 'User Guide',
          },
        ],
      },
            footer: {
                style: 'dark',
                links: [
                    {
                        title: 'Docs',
                        items: [
                            {
                                label: 'User Guide',
                                to: '/docs/intro',
                            },
                        ],
                    },
                    {
                        title: 'Links',
                        items: [
                            {
                                label: 'NOVA Dashboard',
                                href: 'https://nova.ornl.gov',
                            },
                            {
                                label: 'Calvera - ORNL\'s Galaxy instance',
                                href: 'https://calvera.ornl.gov',
                            },
                        ],
                    },
                ],
                copyright: `Copyright © ${new Date().getFullYear()} ORNL. Built with Docusaurus.`,
            },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
      },
    }),
};

export default config;
