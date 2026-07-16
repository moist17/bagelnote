import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const blog = defineCollection({
	// Load Markdown and MDX files in the `src/content/blog/` directory.
	loader: glob({ base: './src/content/blog', pattern: '**/*.{md,mdx}' }),
	// Type-check frontmatter using a schema
	schema: ({ image }) =>
		z.object({
			title: z.string(),
			description: z.string(),
			// Transform string to Date object
			pubDate: z.coerce.date(),
			updatedDate: z.coerce.date().optional(),
			heroImage: z.optional(image()),
		}),
});

const notes = defineCollection({
	// Load Markdown files in the `src/content/notes/` directory.
	loader: glob({ base: './src/content/notes', pattern: '**/*.md' }),
	// Short posts only need a publish date; the body is the note itself.
	schema: z.object({
		pubDate: z.coerce.date(),
	}),
});

export const collections = { blog, notes };
