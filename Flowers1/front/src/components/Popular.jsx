import { useState, useEffect } from "react";
import "../main.css";
import BuyButton from "./buy_button";


const Popular = ({ onAddToCart, goToCatalog }) => {
    const [product, setProduct] = useState([]);
    useEffect(() => {
        fetch("../src/popular.json")
            .then((response) => response.json())
            .then((data) => setProduct(data));
    }, []);
    if (!product) {
        return <div>Loading...</div>;
    }
    if (product.length === 0) {
        return <div>No products found.</div>;
    }
    if (product.length > 0) {
    return (
        <section className="popular">
            <h2 className="popular-title">Популярные цветы</h2>
            <div className="popular-cards">
                {product.map((product, index) => (
                    <div key={index} className="popular-card">
                        <img src={product.image} alt={product.title} className="popular-card-image" />
                        <div className="popular_active">
                            <div className="popular_info">
                                <h3 className="popular-card-title">{product.title}</h3>
                                <p className="popular-card-description">{product.description}</p>
                                <p className="popular-card-price">{product.price} ₽</p>
                            </div>
                            <BuyButton onClick={() => onAddToCart(product)} />
                        </div>
                    </div>
                ))}
            </div>
            <button className="popular-button" onClick={goToCatalog}>
                Показать все
            </button>
        </section>
    );
}}
export default Popular;
