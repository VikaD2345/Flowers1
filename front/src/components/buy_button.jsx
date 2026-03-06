import "../main.css";
const BuyButton = ({ onClick }) => {
    return (
        <button className="popular-card-button" onClick={onClick} type="button">В корзину</button>
    );
}

export default BuyButton;
