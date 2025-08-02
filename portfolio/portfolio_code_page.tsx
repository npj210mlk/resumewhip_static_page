import Link from "next/link"
import Image from "next/image"
import { ArrowRight, Download, Mail, Linkedin, Github } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 w-full border-b bg-background">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold">Jane Smith</span>
            <Badge variant="outline">Product Manager</Badge>
          </div>
          <nav className="hidden md:flex gap-6">
            <Link href="#about" className="text-sm font-medium hover:underline underline-offset-4">
              About
            </Link>
            <Link href="#experience" className="text-sm font-medium hover:underline underline-offset-4">
              Experience
            </Link>
            <Link href="#projects" className="text-sm font-medium hover:underline underline-offset-4">
              Projects
            </Link>
            <Link href="#skills" className="text-sm font-medium hover:underline underline-offset-4">
              Skills
            </Link>
            <Link href="#contact" className="text-sm font-medium hover:underline underline-offset-4">
              Contact
            </Link>
          </nav>
          <Button asChild size="sm">
            <a href="/resume.pdf" download>
              <Download className="mr-2 h-4 w-4" />
              Resume
            </a>
          </Button>
        </div>
      </header>
      <main className="flex-1">
        {/* Hero Section */}
        <section className="w-full py-12 md:py-24 lg:py-32 bg-muted/40">
          <div className="container px-4 md:px-6">
            <div className="grid gap-6 lg:grid-cols-[1fr_400px] lg:gap-12 xl:grid-cols-[1fr_500px]">
              <div className="flex flex-col justify-center space-y-4">
                <div className="space-y-2">
                  <h1 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl lg:text-6xl">
                    Product Manager with a passion for user-centered design
                  </h1>
                  <p className="max-w-[600px] text-muted-foreground md:text-xl">
                    Driving product strategy and execution at the intersection of business, technology, and user
                    experience
                  </p>
                </div>
                <div className="flex flex-col gap-2 min-[400px]:flex-row">
                  <Button asChild>
                    <a href="#projects">
                      View Projects
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </a>
                  </Button>
                  <Button variant="outline" asChild>
                    <a href="#contact">Contact Me</a>
                  </Button>
                </div>
              </div>
              <div className="flex items-center justify-center">
                <Image
                  src="/placeholder.svg?height=500&width=500"
                  alt="Professional headshot"
                  width={400}
                  height={400}
                  className="rounded-full aspect-square object-cover border-4 border-background shadow-xl"
                  priority
                />
              </div>
            </div>
          </div>
        </section>

        {/* About Section */}
        <section id="about" className="w-full py-12 md:py-24 lg:py-32">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">About Me</h2>
                <p className="max-w-[900px] text-muted-foreground md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                  I'm a strategic product manager with 7+ years of experience building digital products that users love.
                  My approach combines data-driven decision making with deep user empathy to deliver products that solve
                  real problems.
                </p>
              </div>
            </div>
            <div className="mx-auto grid max-w-5xl items-center gap-6 py-12 lg:grid-cols-2 lg:gap-12">
              <div className="flex flex-col justify-center space-y-4">
                <ul className="grid gap-6">
                  <li className="flex items-start gap-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-6 w-6"
                      >
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                      </svg>
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-xl font-bold">Strategic Vision</h3>
                      <p className="text-muted-foreground">
                        Translating business objectives into product roadmaps that deliver measurable results
                      </p>
                    </div>
                  </li>
                  <li className="flex items-start gap-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-6 w-6"
                      >
                        <circle cx="12" cy="12" r="10"></circle>
                        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                      </svg>
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-xl font-bold">User-Centered Design</h3>
                      <p className="text-muted-foreground">
                        Advocating for users through research, testing, and iterative design processes
                      </p>
                    </div>
                  </li>
                  <li className="flex items-start gap-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-6 w-6"
                      >
                        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
                        <circle cx="9" cy="7" r="4"></circle>
                        <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                      </svg>
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-xl font-bold">Cross-Functional Leadership</h3>
                      <p className="text-muted-foreground">
                        Collaborating with engineering, design, and business teams to deliver cohesive products
                      </p>
                    </div>
                  </li>
                </ul>
              </div>
              <div className="space-y-4">
                <h3 className="text-2xl font-bold">My Product Philosophy</h3>
                <p className="text-muted-foreground">
                  I believe great products solve real problems in elegant ways. My approach combines rigorous analysis
                  with creative thinking to identify opportunities and craft solutions that users love.
                </p>
                <p className="text-muted-foreground">
                  Throughout my career, I've led product teams through all stages of the product lifecycle, from initial
                  concept to market launch and beyond. I'm passionate about building products that not only meet
                  business objectives but also genuinely improve users' lives.
                </p>
                <p className="text-muted-foreground">
                  When I'm not working on products, you can find me hiking, reading about emerging technologies, or
                  mentoring aspiring product managers.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Experience Section */}
        <section id="experience" className="w-full py-12 md:py-24 lg:py-32 bg-muted/40">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">Work Experience</h2>
                <p className="max-w-[900px] text-muted-foreground md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                  My professional journey in product management
                </p>
              </div>
            </div>
            <div className="mx-auto grid max-w-5xl gap-8 py-12">
              <div className="grid gap-8 md:grid-cols-2">
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-xl font-bold">Senior Product Manager</h3>
                        <p className="text-muted-foreground">TechCorp Inc.</p>
                      </div>
                      <Badge>2020 - Present</Badge>
                    </div>
                    <ul className="space-y-2 text-sm">
                      <li>Led the development of a flagship SaaS platform resulting in 40% revenue growth</li>
                      <li>Managed a cross-functional team of 12 engineers, designers, and data analysts</li>
                      <li>Implemented agile methodologies that reduced time-to-market by 30%</li>
                      <li>Conducted user research that informed product strategy and roadmap priorities</li>
                    </ul>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-xl font-bold">Product Manager</h3>
                        <p className="text-muted-foreground">InnovateSoft</p>
                      </div>
                      <Badge>2017 - 2020</Badge>
                    </div>
                    <ul className="space-y-2 text-sm">
                      <li>Owned the product roadmap for a mobile application with 500K+ monthly active users</li>
                      <li>Increased user retention by 25% through data-driven feature prioritization</li>
                      <li>Collaborated with UX team to redesign core user flows, improving conversion by 15%</li>
                      <li>Defined and tracked KPIs that aligned product development with business goals</li>
                    </ul>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-xl font-bold">Associate Product Manager</h3>
                        <p className="text-muted-foreground">StartupVision</p>
                      </div>
                      <Badge>2015 - 2017</Badge>
                    </div>
                    <ul className="space-y-2 text-sm">
                      <li>Assisted in the launch of an e-commerce platform that achieved $1M in first-year sales</li>
                      <li>Conducted competitive analysis to identify market opportunities</li>
                      <li>Created detailed user stories and acceptance criteria for engineering team</li>
                      <li>Managed the beta testing program with 200+ participants</li>
                    </ul>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-xl font-bold">Business Analyst</h3>
                        <p className="text-muted-foreground">ConsultCo</p>
                      </div>
                      <Badge>2013 - 2015</Badge>
                    </div>
                    <ul className="space-y-2 text-sm">
                      <li>Analyzed business requirements and translated them into functional specifications</li>
                      <li>Supported product team with market research and data analysis</li>
                      <li>Created dashboards to track product performance metrics</li>
                      <li>Facilitated workshops to gather stakeholder requirements</li>
                    </ul>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </section>

        {/* Projects Section */}
        <section id="projects" className="w-full py-12 md:py-24 lg:py-32">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">Featured Projects</h2>
                <p className="max-w-[900px] text-muted-foreground md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                  Case studies showcasing my product management approach and impact
                </p>
              </div>
            </div>
            <div className="mx-auto grid max-w-5xl gap-8 py-12">
              <Tabs defaultValue="all" className="w-full">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="all">All</TabsTrigger>
                  <TabsTrigger value="saas">SaaS</TabsTrigger>
                  <TabsTrigger value="mobile">Mobile</TabsTrigger>
                  <TabsTrigger value="ecommerce">E-commerce</TabsTrigger>
                </TabsList>
                <TabsContent value="all" className="mt-6">
                  <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
                    {projects.map((project, index) => (
                      <ProjectCard key={index} project={project} />
                    ))}
                  </div>
                </TabsContent>
                <TabsContent value="saas" className="mt-6">
                  <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
                    {projects
                      .filter((project) => project.category === "SaaS")
                      .map((project, index) => (
                        <ProjectCard key={index} project={project} />
                      ))}
                  </div>
                </TabsContent>
                <TabsContent value="mobile" className="mt-6">
                  <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
                    {projects
                      .filter((project) => project.category === "Mobile")
                      .map((project, index) => (
                        <ProjectCard key={index} project={project} />
                      ))}
                  </div>
                </TabsContent>
                <TabsContent value="ecommerce" className="mt-6">
                  <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
                    {projects
                      .filter((project) => project.category === "E-commerce")
                      .map((project, index) => (
                        <ProjectCard key={index} project={project} />
                      ))}
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </section>

        {/* Skills Section */}
        <section id="skills" className="w-full py-12 md:py-24 lg:py-32 bg-muted/40">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">Skills & Expertise</h2>
                <p className="max-w-[900px] text-muted-foreground md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                  My product management toolkit and areas of expertise
                </p>
              </div>
            </div>
            <div className="mx-auto grid max-w-5xl gap-8 py-12 md:grid-cols-2">
              <Card>
                <CardContent className="p-6">
                  <h3 className="text-xl font-bold mb-4">Product Management</h3>
                  <div className="grid gap-2">
                    <div className="flex items-center justify-between">
                      <span>Product Strategy</span>
                      <div className="flex">
                        {[1, 2, 3, 4, 5].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-primary mx-0.5" />
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Roadmap Planning</span>
                      <div className="flex">
                        {[1, 2, 3, 4, 5].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-primary mx-0.5" />
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>User Research</span>
                      <div className="flex">
                        {[1, 2, 3, 4].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-primary mx-0.5" />
                        ))}
                        <div className="w-4 h-4 rounded-full bg-muted mx-0.5" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Agile Methodologies</span>
                      <div className="flex">
                        {[1, 2, 3, 4, 5].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-primary mx-0.5" />
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Competitive Analysis</span>
                      <div className="flex">
                        {[1, 2, 3, 4].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-primary mx-0.5" />
                        ))}
                        <div className="w-4 h-4 rounded-full bg-muted mx-0.5" />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-6">
                  <h3 className="text-xl font-bold mb-4">Technical Skills</h3>
                  <div className="grid gap-2">
                    <div className="flex items-center justify-between">
                      <span>Data Analysis</span>
                      <div className="flex">
                        {[1, 2, 3, 4].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-primary mx-0.5" />
                        ))}
                        <div className="w-4 h-4 rounded-full bg-muted mx-0.5" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>SQL</span>
                      <div className="flex">
                        {[1, 2, 3].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-primary mx-0.5" />
                        ))}
                        {[1, 2].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-muted mx-0.5" />
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Wireframing</span>
                      <div className="flex">
                        {[1, 2, 3, 4].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-primary mx-0.5" />
                        ))}
                        <div className="w-4 h-4 rounded-full bg-muted mx-0.5" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>A/B Testing</span>
                      <div className="flex">
                        {[1, 2, 3, 4, 5].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-primary mx-0.5" />
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Technical Documentation</span>
                      <div className="flex">
                        {[1, 2, 3, 4].map((i) => (
                          <div key={i} className="w-4 h-4 rounded-full bg-primary mx-0.5" />
                        ))}
                        <div className="w-4 h-4 rounded-full bg-muted mx-0.5" />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-6">
                  <h3 className="text-xl font-bold mb-4">Tools</h3>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">Jira</Badge>
                    <Badge variant="secondary">Confluence</Badge>
                    <Badge variant="secondary">Figma</Badge>
                    <Badge variant="secondary">Amplitude</Badge>
                    <Badge variant="secondary">Mixpanel</Badge>
                    <Badge variant="secondary">Google Analytics</Badge>
                    <Badge variant="secondary">Tableau</Badge>
                    <Badge variant="secondary">Miro</Badge>
                    <Badge variant="secondary">Notion</Badge>
                    <Badge variant="secondary">Asana</Badge>
                    <Badge variant="secondary">Trello</Badge>
                    <Badge variant="secondary">Slack</Badge>
                    <Badge variant="secondary">Microsoft Office</Badge>
                    <Badge variant="secondary">G Suite</Badge>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-6">
                  <h3 className="text-xl font-bold mb-4">Certifications</h3>
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-5 w-5 text-primary"
                      >
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                      </svg>
                      <span>Certified Scrum Product Owner (CSPO)</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-5 w-5 text-primary"
                      >
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                      </svg>
                      <span>Product Management Certification (PMC)</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-5 w-5 text-primary"
                      >
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                      </svg>
                      <span>Google Analytics Certification</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-5 w-5 text-primary"
                      >
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                      </svg>
                      <span>MBA, Business Administration</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* Contact Section */}
        <section id="contact" className="w-full py-12 md:py-24 lg:py-32">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">Get In Touch</h2>
                <p className="max-w-[900px] text-muted-foreground md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                  Let's connect to discuss opportunities and collaborations
                </p>
              </div>
            </div>
            <div className="mx-auto grid max-w-5xl gap-8 py-12 md:grid-cols-2">
              <Card>
                <CardContent className="p-6">
                  <div className="grid gap-4">
                    <div className="flex items-center gap-4">
                      <Mail className="h-6 w-6 text-primary" />
                      <div>
                        <h3 className="font-semibold">Email</h3>
                        <p className="text-sm text-muted-foreground">jane.smith@example.com</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <Linkedin className="h-6 w-6 text-primary" />
                      <div>
                        <h3 className="font-semibold">LinkedIn</h3>
                        <a href="https://linkedin.com/in/janesmith" className="text-sm hover:underline">
                          linkedin.com/in/janesmith
                        </a>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <Github className="h-6 w-6 text-primary" />
                      <div>
                        <h3 className="font-semibold">GitHub</h3>
                        <a href="https://github.com/janesmith" className="text-sm hover:underline">
                          github.com/janesmith
                        </a>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-6">
                  <form className="grid gap-4">
                    <div className="grid gap-2">
                      <label
                        htmlFor="name"
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                      >
                        Name
                      </label>
                      <input
                        id="name"
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        placeholder="Your name"
                      />
                    </div>
                    <div className="grid gap-2">
                      <label
                        htmlFor="email"
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                      >
                        Email
                      </label>
                      <input
                        id="email"
                        type="email"
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        placeholder="Your email"
                      />
                    </div>
                    <div className="grid gap-2">
                      <label
                        htmlFor="message"
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                      >
                        Message
                      </label>
                      <textarea
                        id="message"
                        className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        placeholder="Your message"
                      />
                    </div>
                    <Button type="submit" className="w-full">
                      Send Message
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>
      </main>
      <footer className="w-full border-t bg-background">
        <div className="container flex flex-col items-center justify-between gap-4 py-10 md:h-24 md:flex-row md:py-0">
          <div className="flex flex-col items-center gap-4 px-8 md:flex-row md:gap-2 md:px-0">
            <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
              © 2025 Jane Smith. All rights reserved.
            </p>
          </div>
          <div className="flex gap-4">
            <a href="https://linkedin.com/in/janesmith" target="_blank" rel="noreferrer">
              <Linkedin className="h-5 w-5 text-muted-foreground hover:text-foreground" />
              <span className="sr-only">LinkedIn</span>
            </a>
            <a href="https://github.com/janesmith" target="_blank" rel="noreferrer">
              <Github className="h-5 w-5 text-muted-foreground hover:text-foreground" />
              <span className="sr-only">GitHub</span>
            </a>
            <a href="mailto:jane.smith@example.com">
              <Mail className="h-5 w-5 text-muted-foreground hover:text-foreground" />
              <span className="sr-only">Email</span>
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}

// Sample project data
const projects = [
  {
    title: "Enterprise SaaS Platform",
    description:
      "Led the development of a B2B SaaS platform that streamlined workflow management for enterprise clients.",
    image: "/placeholder.svg?height=300&width=400",
    category: "SaaS",
    tags: ["Product Strategy", "UX Research", "Enterprise"],
    link: "#",
  },
  {
    title: "Mobile Banking App",
    description:
      "Redesigned a mobile banking application that improved user engagement by 35% and received a 4.8/5 app store rating.",
    image: "/placeholder.svg?height=300&width=400",
    category: "Mobile",
    tags: ["Mobile", "Fintech", "UX Design"],
    link: "#",
  },
  {
    title: "E-commerce Platform",
    description:
      "Developed an e-commerce platform with personalized recommendations that increased average order value by 24%.",
    image: "/placeholder.svg?height=300&width=400",
    category: "E-commerce",
    tags: ["E-commerce", "Personalization", "Analytics"],
    link: "#",
  },
  {
    title: "Analytics Dashboard",
    description: "Created a real-time analytics dashboard that provided actionable insights for marketing teams.",
    image: "/placeholder.svg?height=300&width=400",
    category: "SaaS",
    tags: ["Data Visualization", "Real-time Analytics", "B2B"],
    link: "#",
  },
  {
    title: "Fitness Tracking App",
    description:
      "Managed the development of a fitness tracking app with social features that achieved 100K downloads in the first month.",
    image: "/placeholder.svg?height=300&width=400",
    category: "Mobile",
    tags: ["Health Tech", "Social", "Gamification"],
    link: "#",
  },
  {
    title: "Subscription Marketplace",
    description:
      "Built a subscription-based marketplace connecting service providers with customers, generating $2M in GMV within the first year.",
    image: "/placeholder.svg?height=300&width=400",
    category: "E-commerce",
    tags: ["Marketplace", "Subscription", "Service Economy"],
    link: "#",
  },
]

// Project Card Component
function ProjectCard({ project }) {
  return (
    <Card className="overflow-hidden">
      <div className="aspect-video w-full overflow-hidden">
        <Image
          src={project.image || "/placeholder.svg"}
          alt={project.title}
          width={400}
          height={300}
          className="object-cover w-full h-full transition-transform hover:scale-105"
        />
      </div>
      <CardContent className="p-6">
        <h3 className="text-xl font-bold mb-2">{project.title}</h3>
        <p className="text-muted-foreground text-sm mb-4">{project.description}</p>
        <div className="flex flex-wrap gap-2 mb-4">
          {project.tags.map((tag, index) => (
            <Badge key={index} variant="outline">
              {tag}
            </Badge>
          ))}
        </div>
        <Button asChild variant="outline" size="sm" className="w-full bg-transparent">
          <a href={project.link}>View Case Study</a>
        </Button>
      </CardContent>
    </Card>
  )
}
