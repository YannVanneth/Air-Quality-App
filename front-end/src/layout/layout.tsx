import { ReactNode } from "react"
import Header from '../components/Header';
import Footer from '../components/Footer';

const Layout = ({ children }: { children: ReactNode }) => {
    return (
        <section>
            <Header />
            <main>
                {children}
            </main>
            <Footer />
        </section>
    )
}

export default Layout